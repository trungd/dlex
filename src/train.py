import os
import torch
# import curses
from torch.utils.data import DataLoader
from tqdm import tqdm
from datetime import datetime

from configs import Configs
from utils.model_utils import get_model, get_dataset, get_optimizer, load_checkpoint, save_checkpoint, add_result
from utils.logging import logger, set_log_dir
from utils.ops_utils import Tensor, LongTensor
from utils.utils import init_dirs
from eval import eval

def train(params, args):
    torch.manual_seed(params.seed)

    Dataset = get_dataset(params)
    Model = get_model(params)

    logger.info("Dataset: %s. Model: %s" % (str(Dataset), str(Model)))

    # Init dataset
    Dataset.prepare(force=args.force_preprocessing)
    if args.debug:
        dataset_train = Dataset("debug", params)
        dataset_test = Dataset("debug", params)
    else:
        dataset_train = Dataset("train", params)
        dataset_test = Dataset("test", params)

    # Init model
    model = Model(params, dataset_train)
    if torch.cuda.is_available():
        logger.info("Cuda available: " + torch.cuda.get_device_name(0))
        model.cuda()

    # Init optimizer
    optim = get_optimizer(params, model)

    if args.load:
        load_checkpoint(args.load, params, model, optim)
        init_dirs(params)
        logger.info("Saved model loaded: %s" % args.load)
        logger.info("Epoch: %f" % (model.global_step / len(dataset_train)))
    else:
        params.set('training_id', datetime.now().strftime('%Y%m%d-%H%M%S'))
        init_dirs(params)

    logger.info("Train size: %d" % len(dataset_train))

    data_train = DataLoader(
        dataset_train,
        batch_size=params.batch_size,
        shuffle=params.shuffle,
        collate_fn=dataset_train.collate_fn)

    if not args.train:
        logger.info("Abort without training.")
        return

    logger.info("Training model...")

    epoch = int(model.global_step / len(dataset_train))
    for ei in range(epoch + 1, epoch + params.num_epochs + 1):
        logger.info("--- Epoch %d ---" % ei)
        loss_sum = 0

        epoch_step = 0
        for id, batch in enumerate(tqdm(data_train, desc="Epoch %d" % ei)):
            model.zero_grad()
            loss = model.loss(batch)
            loss.backward()
            optim.step()
            loss_sum += loss.item()

            epoch_step += 1
            if args.debug and epoch_step > 10:
                break

            model.global_step = (ei - 1) * len(dataset_train) + id * params.batch_size

        res, best_res = eval(model, dataset_test, params, save_result=True)
        for metric in best_res:
            if best_res[metric] == res:
                save_checkpoint(
                    "best" if len(params.metrics) == 1 else "best-%s" % metric,
                    params, model, optim)
                logger.info("Best checkpoint for %s saved" % metric)

        logger.info(str(res))
        #logger.info("Loss: %f, Acc: %f" % (loss, res))
        save_checkpoint("epoch-%02d" % ei, params, model, optim)

def main():
    configs = Configs(mode="train")
    train(configs.params, configs.args)

if __name__ == "__main__":
    main()
