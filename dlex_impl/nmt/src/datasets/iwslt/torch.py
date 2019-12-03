import os
import random

from dlex.datasets.nlp.utils import Vocab
from dlex.datasets.seq2seq.torch import PytorchSeq2SeqDataset
from dlex.utils.logging import logger
from dlex.torch import BatchItem


class IWSLT15EnglishVietnamese(PytorchSeq2SeqDataset):
    def __init__(self, builder, mode):
        super().__init__(
            builder, mode,
            vocab_path=os.path.join(builder.get_raw_data_dir(), "vocab.%s" % builder.params.dataset.target))

        self._src_vocab = Vocab(os.path.join(builder.get_raw_data_dir(), "vocab.%s" % builder.params.dataset.source))
        self._data = self._load_data()

    @property
    def input_size(self):
        return len(self._src_vocab)

    def _load_data(self):
        data_file_names = {
            "train": {"en": "train.en", "vi": "train.vi"},
            "test": {"en": "tst2012.en", "vi": "tst2012.vi"}
        }
        # Load data
        if self.mode in ["train", "test"]:
            data = []
            src_data = open(
                os.path.join(self.builder.get_raw_data_dir(), data_file_names[self.mode][self.params.dataset.source]), "r",
                encoding='utf-8').read().split("\n")
            tgt_data = open(
                os.path.join(self.builder.get_raw_data_dir(), data_file_names[self.mode][self.params.dataset.target]), "r",
                encoding='utf-8').read().split("\n")
            for src, tgt in zip(src_data, tgt_data):
                X = [self._src_vocab.get_token_id(tkn) for tkn in src.split(' ')]
                Y = [self.vocab.get_token_id(tkn) for tkn in tgt.split(' ')]
                if self.params.dataset.max_source_length and len(X) > self.params.dataset.max_source_length or \
                        self.params.dataset.max_target_length and len(Y) > self.params.dataset.max_target_length:
                    continue
                data.append(BatchItem(X=X, Y=Y))
            logger.debug("Data sample: %s", str(random.choice(data)))
            return data
        elif self.mode == "infer":
            return []