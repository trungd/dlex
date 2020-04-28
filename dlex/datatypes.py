import os
import pickle
import time
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Union

import numpy as np
from dlex.utils import logger, table2str


class ModelReport:
    launch_time: datetime = None

    params = None

    results: Union[Dict[str, float], List[Dict[str, float]]] = None
    epoch_results: Dict[str, List[Dict[str, float]]] = None
    current_test_results: Dict[str, Dict[str, float]] = None
    epoch_valid_results: List[Dict[str, float]] = None
    epoch_test_results: List[Dict[str, float]] = None
    epoch_losses: List[float] = None
    status: str = None
    num_params: int = None
    num_trainable_params: int = None
    param_details: str = None
    summary_writer = None

    def __init__(self, training_idx):
        self.training_idx = training_idx

    def add_epoch_results(self, results):
        self.current_test_results = results

    @property
    def current_epoch(self) -> int:
        if len(self.epoch_results) == 0:
            return 1
        return min(len(res) for res in self.epoch_results.values()) + 1

    @property
    def num_epochs(self) -> int:
        return self.params.train.num_epochs

    def finish(self):
        self.status = "finished"

    @property
    def metrics(self) -> List[str]:
        if self.params:
            return self.params.test.metrics

    def get_result_text(self, metric, full=False):
        """
        Get progress and current result in readable text format. Text includes:
            - Result / Average result ± variance
            - Current epoch
            - Current fold (k-fold cross validation)
        :param metric:
        :return:
        """
        if not self.results:
            if self.current_results:
                res = self.current_results[metric]
                return "%.2f" % res
            else:
                return "-"
        else:
            res = self.results[metric]
            if type(res) == float:
                return "%.2f" % res
            elif type(res) == list and len(res) > 0:  # cross validation
                if full:
                    return "[" + ", ".join(["%.2f" % r for r in res]) + "] -> " + "%.2f ± %.2f" % (np.mean(res), np.std(res))
                else:
                    return "%.2f ± %.2f" % (np.mean(res), np.std(res))
            else:
                return "-"

    def get_status_text(self):
        if self.status == "finished":
            status = "done"
        elif self.params.train.cross_validation is not None:
            current_fold = len(self.results[self.metrics[0]])
            status = f"CV {current_fold}/{self.params.train.cross_validation}"
        else:
            pbar = get_progress_bar(10, (self.current_epoch - 1) / self.num_epochs)
            status = f"{pbar} {self.current_epoch - 1}/{self.num_epochs}"
        return status

    def set_model_summary(
            self,
            variable_names: List[str],
            variable_shapes: List[List[int]],
            variable_trainable: List[bool]):
        parameter_details = [["Name", "Shape", "Trainable"]]
        num_params = 0
        num_trainable_params = 0
        for name, shape, trainable in zip(variable_names, variable_shapes, variable_trainable):
            parameter_details.append([
                name,
                str(list(shape)),
                "✓" if trainable else ""])
            num_params += np.prod(list(shape))
            if trainable:
                num_trainable_params += np.prod(list(shape))

        s = table2str(parameter_details)
        logger.debug(f"Model parameters\n{s}")
        logger.debug(" - ".join([
            f"No. parameters: {num_params:,}",
            f"No. trainable parameters: {num_trainable_params:,}"
        ]))

        self.num_params = num_params
        self.num_trainable_params = num_trainable_params

    def save(self):
        path = os.path.join(self.params.log_dir, f"report_{self.training_idx}.pkl")
        logger.debug(f"Report saved to {path}")
        with open(path, "wb") as f:
            pickle.dump(self, f)

    @classmethod
    def load(cls, log_dir, training_idx):
        path = os.path.join(log_dir, f"report_{training_idx}.pkl")
        if not os.path.exists(path):
            return None
        with open(path, "rb") as f:
            return pickle.load(f)


class TrainingProgress:
    last_save = 0
    last_log = 0
    current_epoch = 0
    epoch_num_samples = 0

    def __init__(self, params, num_samples):
        self.params = params
        self.num_samples = num_samples
        self.batch_size = params.train.batch_size

    @property
    def epoch_progress(self) -> float:
        return min(1., self.epoch_num_samples / self.num_samples)

    def update(self, num):
        self.epoch_num_samples += num

    def new_epoch(self, current_epoch):
        logger.info(f"Training epoch {current_epoch}...")
        self.current_epoch = current_epoch

    def check_interval_passed(self, last_done: float, interval: str) -> (bool, float):
        if not interval:
            return False, last_done
        unit = interval[-1]
        value = float(interval[:-1])
        if unit == "e":  # epoch progress (percentage)
            if self.epoch_progress - last_done >= value:
                return True, self.epoch_progress
            else:
                return False, last_done
        elif unit in ["s", "m", "h"]:
            d = dict(s=1, m=60, h=3600)[unit]
            if time.time() / d - last_done > value:
                return True, time.time() / d
            else:
                return False, last_done

    def should_save(self):
        is_passed, self.last_save = self.check_interval_passed(self.last_save, self.params.train.save_every)
        return is_passed

    def should_log(self):
        is_passed, self.last_log = self.check_interval_passed(self.last_log, self.params.train.log_every)
        return is_passed


def get_progress_bar(width, percent):
    progress = int(width * percent)
    return "[%s%s]" % ('#' * progress, ' ' * (width - progress))