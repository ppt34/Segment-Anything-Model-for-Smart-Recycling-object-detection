
#################################################
### THIS FILE WAS AUTOGENERATED! DO NOT EDIT! ###
#################################################
# file to edit: dev_nb/03_Sampler.ipynb

from torch.utils.data import Sampler, RandomSampler, SequentialSampler
import torch
from torch import tensor
import numpy as np

def get_samplers(god):
    samplers = {}
    for phase in ('train', 'val'):
        sampling_dict = god.config['sampling'][phase]
        ds = god.datasets[phase]

        if sampling_dict['name'] == 'sequential':
            samplers[phase] = SequentialSampler(ds)

        elif sampling_dict['name']  == 'random':
            samplers[phase] = RandomSampler(ds)

        elif sampling_dict['name'] == 'undersample':
            targets = tensor([ds.get_y(i) for i in range(len(ds))])
            #targets = torch.cat([yb for _, yb in DataLoader(ds, batch_size=64, num_workers=12)])
            samplers[phase] = UnderSampler(targets)

        elif sampling_dict['name'] == 'oversample':
            targets = tensor([ds.get_y(i) for i in range(len(ds))])
            #targets = torch.cat([yb for _, yb in DataLoader(ds, batch_size=64, num_workers=12)])
            samplers[phase] = OverSampler(targets)

        elif sampling_dict['name'] == 'random_subset':
            targets = tensor([ds.get_y(i) for i in range(len(ds))])
            samplers[phase] = RandomSubsetSampler(targets, fraction=sampling_dict['fraction'])

        elif sampling_dict['name'] == 'n_sample':
            targets = tensor([ds.get_y(i) for i in range(len(ds))])
            use_class_counts = 'class_counts' in sampling_dict
            use_samples_per_class = 'n_samples_per_class' in sampling_dict

            if use_class_counts and use_samples_per_class:
                raise ValueError("Only one of 'class_counts' or 'samples_per_class' should be provided in sampler settings.")
            elif use_class_counts:
                samplers[phase] = NSampler(targets, class_counts=sampling_dict['class_counts'])
            elif use_samples_per_class:
                samplers[phase] = NSampler(targets, sampling_dict['n_samples_per_class'])
            else:
                raise ValueError("One of 'class_counts' or 'samples_per_class' sampler_settings must be provided.")

        else:
            raise Exception(f"Sampling method '{sampling_dict['name']}' is not supported")

    return samplers

class UnderSampler(Sampler):
    def __init__(self, targets):
        if type(targets) == list: targets = torch.tensor(targets)
        self.class_idx_dict = {c: (targets == c).nonzero(as_tuple=True)[0] for c in targets.unique()}
        self.min_class_len = min(len(idx) for idx in self.class_idx_dict.values())

    def __iter__(self):
        shuffled_class_idx = [idx[torch.randperm(len(idx))] for idx in self.class_idx_dict.values()]
        same_size_class_idx = [idx[:self.min_class_len] for idx in shuffled_class_idx]
        balanced_class_idx = torch.cat(same_size_class_idx)[torch.randperm(self.__len__())]
        return iter(balanced_class_idx.tolist())

    def __len__(self):
        return len(self.class_idx_dict) * self.min_class_len


class OverSampler(Sampler):
    def __init__(self, targets):
        if type(targets) == list:
            targets = torch.tensor(targets)

        self.class_idx_dict = {c: (targets == c).nonzero(as_tuple=True)[0] for c in targets.unique()}
        self.max_class_len = max(len(idx) for idx in self.class_idx_dict.values())

    def __iter__(self):
        oversampled_class_idx = [torch.cat([idx[torch.randint(high=len(idx), size=(self.max_class_len,))]
                                            for _ in range((self.max_class_len + len(idx) - 1) // len(idx))])[:self.max_class_len]
                                for idx in self.class_idx_dict.values()]
        oversampled_class_idx = torch.cat(oversampled_class_idx)[torch.randperm(self.__len__())]
        return iter(oversampled_class_idx.tolist())

    def __len__(self):
        return len(self.class_idx_dict) * self.max_class_len

class NSampler(Sampler):
    def __init__(self, targets, n_samples_per_class=None, class_counts=None):
        # Ensure exactly one of n_samples_per_class or class_counts is provided
        if (n_samples_per_class is None) == (class_counts is None):
            raise ValueError("Exactly one of n_samples_per_class or class_counts must be provided.")

        if type(targets) == list: targets = torch.tensor(targets)
        self.n_samples_per_class = n_samples_per_class
        self.class_counts = class_counts
        self.class_idx_dict = {c: (targets == c).nonzero(as_tuple=True)[0] for c in targets.unique()}

    def __iter__(self):
        shuffled_and_resampled_class_idx = []
        for c, idx in self.class_idx_dict.items():
            if self.n_samples_per_class is not None:
                samples_per_class = self.n_samples_per_class
            else:  # self.class_counts is not None
                samples_per_class = self.class_counts[c]

            if len(idx) < samples_per_class:
                repeat_times = samples_per_class // len(idx)
                remainder = samples_per_class % len(idx)
                idx = torch.cat([idx]*repeat_times)
                if remainder:
                    idx = torch.cat([idx, idx[torch.randperm(len(idx))[:remainder]]])
            else:
                idx = idx[torch.randperm(len(idx))][:samples_per_class]
            shuffled_and_resampled_class_idx.append(idx)
        balanced_class_idx = torch.cat(shuffled_and_resampled_class_idx)[torch.randperm(self.__len__())]
        return iter(balanced_class_idx.tolist())

    def __len__(self):
        if self.n_samples_per_class is not None:
            return len(self.class_idx_dict) * self.n_samples_per_class
        else:  # self.class_counts is not None
            return sum(self.class_counts[c] for c in self.class_idx_dict.keys())

class RandomSubsetSampler(Sampler):
    def __init__(self, targets, fraction=0.1):
        self.targets = targets
        self.fraction = fraction

    def __iter__(self):
        class_indices = {}
        for idx, class_label in enumerate(self.targets):
            if class_label.item() not in class_indices:
                class_indices[class_label.item()] = []
            class_indices[class_label.item()].append(idx)

        stratified_indices = []
        for class_label in class_indices:
            indices = class_indices[class_label]
            subset_size = int(len(indices) * self.fraction)
            subset_indices = np.random.choice(indices, size=subset_size, replace=False)
            stratified_indices.extend(subset_indices.tolist())
        np.random.shuffle(stratified_indices)
        return iter(stratified_indices)

    def __len__(self):
        return int(len(self.targets) * self.fraction)