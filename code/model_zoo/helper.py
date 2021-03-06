from urllib.request import urlretrieve
import tarfile
import os
import sys
import pickle
import numpy as np


def download_and_extract_cifar(target_dir,
                               cifar_url='http://www.cs.toronto.edu/'
                               '~kriz/cifar-10-python.tar.gz'):

    if not os.path.exists(target_dir):
        os.mkdir(target_dir)

    fbase = os.path.basename(cifar_url)
    fpath = os.path.join(target_dir, fbase)

    if not os.path.exists(fpath):
        def get_progress(count, block_size, total_size):
            sys.stdout.write('\rDownloading ... %s %d%%' % (fbase,
                             float(count * block_size) /
                             float(total_size) * 100.0))
            sys.stdout.flush()
        local_filename, headers = urlretrieve(cifar_url,
                                              fpath,
                                              reporthook=get_progress)
        sys.stdout.write('\nDownloaded')

    else:
        sys.stdout.write('Found existing')

    statinfo = os.stat(fpath)
    file_size = statinfo.st_size / 1024**2
    sys.stdout.write(' %s (%.1f Mb)\n' % (fbase, file_size))
    sys.stdout.write('Extracting %s ...\n' % fbase)
    sys.stdout.flush()

    with tarfile.open(fpath, 'r:gz') as t:
        t.extractall(target_dir)

    return fpath.replace('cifar-10-python.tar.gz', 'cifar-10-batches-py')


def unpickle_cifar(fpath):
    with open(fpath, 'rb') as f:
        dct = pickle.load(f, encoding='bytes')
    return dct


class Cifar10Loader():
    def __init__(self, cifar_path):
        self.cifar_path = cifar_path
        self.batchnames = [os.path.join(self.cifar_path, f)
                           for f in os.listdir(self.cifar_path)
                           if f.startswith('data_batch')]
        self.testname = os.path.join(self.cifar_path, 'test_batch')
        self.num_train = self.count_train()
        self.num_test = self.count_test()

    def load_test(self, onehot=True, normalize=True):
        dct = unpickle_cifar(self.testname)
        dct[b'labels'] = np.array(dct[b'labels'], dtype=int)

        if onehot:
            dct[b'labels'] = (np.arange(10) ==
                              dct[b'labels'][:, None]).astype(int)

        if normalize:
            dct[b'data'] = dct[b'data'].astype(np.float32)
            dct[b'data'] = dct[b'data'] / 255.0
            
        dct[b'data'] = dct[b'data'].reshape(dct[b'data'].shape[0], 3, 32, 32).transpose(0, 2, 3, 1)
        return dct[b'data'], dct[b'labels']

    def load_train_epoch(self, batch_size=50, onehot=True,
                         shuffle=False, normalize=True, seed=None):

        rgen = np.random.RandomState(seed)

        for batch in self.batchnames:
            dct = unpickle_cifar(batch)
            dct[b'labels'] = np.array(dct[b'labels'], dtype=int)
            dct[b'data'] = dct[b'data'].reshape(dct[b'data'].shape[0], 3, 32, 32).transpose(0, 2, 3, 1)

            if onehot:
                dct[b'labels'] = (np.arange(10) ==
                                  dct[b'labels'][:, None]).astype(int)

            arrays = [dct[b'data'], dct[b'labels']]
            
            del dct

            if normalize:
                arrays[0] = arrays[0].astype(np.float32)
                arrays[0] = np.multiply(arrays[0], 1.0 / 255.0)

            indices = np.arange(arrays[0].shape[0])

            if shuffle:
                rgen.shuffle(indices)

            for start_idx in range(0, indices.shape[0] - batch_size + 1,
                                   batch_size):
                index_slice = indices[start_idx:start_idx + batch_size]
                yield (ary[index_slice] for ary in arrays)

    def count_train(self):
        cnt = 0
        for f in self.batchnames:
            dct = unpickle_cifar(f)
            cnt += len(dct[b'labels'])
        return cnt

    def count_test(self):
        dct = unpickle_cifar(self.testname)
        return len(dct[b'labels'])