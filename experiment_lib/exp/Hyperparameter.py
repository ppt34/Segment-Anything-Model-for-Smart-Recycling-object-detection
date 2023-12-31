
#################################################
### THIS FILE WAS AUTOGENERATED! DO NOT EDIT! ###
#################################################
# file to edit: dev_nb/05_Hyperparameter.ipynb

import torch
from torch import tensor
from torch import nn, optim
from torch.optim import lr_scheduler
import torch.nn.functional as F
from torch_lr_finder import LRFinder

# TODO add a way to pass reduction as optional param
def get_criterion(god):

    def get_criterion_kwargs():
        criterion_config = god.config['hp']['criterion']
        reduction = criterion_config['reduction'] if 'reduction' in criterion_config else 'mean'
        return {'reduction': reduction}
        # !!! weight kwarg is WIP !!!
        # if 'weight' in criterion_config:
        #     if criterion_config['weight'] == 'autobalanced':
        #         auto_weight = 1 - (tensor(config['train_class_counts']) / tensor(config['train_class_counts']).sum())
        #         kwargs['weight'] = auto_weight.to(device if not force_cpu else 'cpu')
        #     else:
        #         kwargs['weight'] = criterion_config['weight'].to(device if not force_cpu else 'cpu')

    criterion_name = god.config['hp']['criterion']['name']
    criterion_kwargs = get_criterion_kwargs()
    clf_type = god.config['model']['classification_type']

    if criterion_name == 'L1Loss' and clf_type == 'binary':
        criterion = nn.L1Loss(**criterion_kwargs)
        return lambda pred,inp: criterion(pred.squeeze(-1), inp.float())

    elif criterion_name == 'MSELoss' and clf_type == 'binary':
        criterion = nn.MSELoss(**criterion_kwargs)
        return lambda pred,inp: criterion(pred.squeeze(-1), inp.float())

    elif criterion_name == 'BCELoss' and clf_type == 'binary':
        criterion = nn.BCELoss(**criterion_kwargs)
        return lambda pred,inp: criterion(pred.squeeze(-1), inp.float())

    elif criterion_name == 'BCEWithLogitsLoss' and clf_type == 'custom':
        criterion = nn.BCEWithLogitsLoss(**criterion_kwargs)
        return lambda pred,inp: criterion(pred.squeeze(-1), inp.float())

    elif criterion_name == 'CrossEntropyLoss' and clf_type == 'multiclass':
        return nn.CrossEntropyLoss(**criterion_kwargs)

    elif criterion_name == 'HierarchicalLoss' and clf_type == 'fish_hierarchical':
        return HierarchicalLoss(**criterion_kwargs)

    elif criterion_name == 'L1Loss' and clf_type == 'multiclass_sigmoid':
        criterion = nn.L1Loss(**criterion_kwargs)
        return lambda pred,inp: criterion(pred,  F.one_hot(inp, num_classes=8)) # TODO determine num_classes from config

    elif criterion_name == 'BCELoss' and clf_type == 'multiclass_sigmoid':
        criterion = nn.BCELoss(**criterion_kwargs)
        return lambda pred,inp: criterion(pred, F.one_hot(inp, num_classes=8).float()) # TODO determine num_classes from config

    elif criterion_name == 'BCELoss' and clf_type == 'multiclass_threshold':
        criterion = nn.BCELoss(**criterion_kwargs)
        return lambda pred,inp: criterion(pred, ((inp-1).unsqueeze(-1) == torch.arange(7, device=pred.device)).float()) # TODO determine num_classes (-1) from config

    elif criterion_name == 'SoftF1Loss' and clf_type == 'multiclass':
        return SoftF1Loss(**criterion_kwargs)

    else:
        raise Exception(f"get_criterion has no implementation for config with criterion '{criterion_name}' and classification_type '{clf_type}'")

def get_optimizer(god, custom_lr=None):
    optim_name = god.config['hp']['optimizer']['name']
    if optim_name == 'SGD':
        optim_class = optim.SGD
    elif optim_name == 'Adam':
        optim_class = optim.Adam
    else:
        raise Exception(f"Optimizer with name '{optim_name}' current not supported.")

    return optim_class([p for p in god.model.parameters() if p.requires_grad], lr=custom_lr or god.config['hp']['learning_rate'])

def get_scheduler(god):
    sched_config = god.config['hp']['scheduler']
    if sched_config == 'None':
        return None
    if sched_config['name'] == 'OneCycleLr':
        return lr_scheduler.OneCycleLR(
               god.optimizer,
               max_lr = sched_config['max_lr'],
               steps_per_epoch = len(god.dataloaders['train']),
               epochs = god.config['training']['n_epochs'],
               anneal_strategy = sched_config['anneal_strategy'])

    raise Exception(f"Scheduler with name '{sched_config['name']}' is not supported yet")

def run_lr_finder(god):
    lr_finder = LRFinder(god.model, god.optimizer, god.criterion, device='cuda')
    lr_finder.range_test(god.dataloaders['train'], end_lr=100, num_iter=100)
    lr_finder.plot() # to inspect the loss-learning rate graph
    lr_finder.reset() # to reset the model and optimizer to their initial state

class HierarchicalLoss(nn.Module):
    def __init__(self, reduction=None, weight=None):
        if weight is not None:
            raise Exception('Weight parameter currently not supported by HierarchicalLoss')

        super(HierarchicalLoss, self).__init__()
        self.loss_fn = nn.CrossEntropyLoss(reduction=reduction)

    def forward(self, outputs, targets):
        fish_not_fish_output, fish_type_output = outputs

        # Create "fish or not fish" labels based on the fish type labels
        fish_not_fish_target = (targets > 0).long()

        fish_not_fish_loss = self.loss_fn(fish_not_fish_output, fish_not_fish_target)

        # Only consider the fish type loss for the samples that are actually fish
        fish_mask = fish_not_fish_target == 1
        if fish_mask.sum() > 0:
            fish_type_loss = self.loss_fn(fish_type_output[fish_mask], targets[fish_mask] - 1)  # -1 to shift the fish type labels to start from 0
        else:
            fish_type_loss = 0

        return fish_not_fish_loss + fish_type_loss

class SoftF1Loss(nn.Module):
    def __init__(self, epsilon=1e-7, reduction=None, weight=None):
        super(SoftF1Loss, self).__init__()
        self.epsilon = epsilon

    def forward(self, logits, labels):
        # Sigmoid activation to get probabilities
        probs = torch.sigmoid(logits)

        # Soft versions of precision and recall
        tp = torch.sum(labels * probs, dim=0)
        fp = torch.sum((1 - labels) * probs, dim=0)
        fn = torch.sum(labels * (1 - probs), dim=0)

        soft_precision = tp / (tp + fp + self.epsilon)
        soft_recall = tp / (tp + fn + self.epsilon)

        # Soft F1 score
        soft_f1 = 2 * (soft_precision * soft_recall) / (soft_precision + soft_recall + self.epsilon)
        # Since we want to minimize the loss, we return 1 - soft_f1
        return 1 - torch.mean(soft_f1)