
#################################################
### THIS FILE WAS AUTOGENERATED! DO NOT EDIT! ###
#################################################
# file to edit: dev_nb/06_Training.ipynb

from tqdm.notebook import tqdm
import torch

def get_device(god):
    if torch.cuda.is_available():
        return torch.device('cuda')
    else:
        print('Warning: No cuda device found.')
        return torch.device('cpu')

def one_episode(god):
    god.before_episode()

    n_epochs = god.config['training']['n_epochs']
    use_progress_bar = god.config['training']['output']['progress_bar']['epoch']
    for epoch in tqdm(range(1, n_epochs+1)) if use_progress_bar else range(1, n_epochs+1):
        one_epoch(god)

    god.after_episode()

def one_epoch(god):
    god.before_epoch()

    for phase in ('train', 'val'):
        if phase == 'train':
            god.model.train()
        elif (god.state['epoch_nr'] % god.config['training'].get('val_frequency', 1)) == 0:
            god.model.eval()
        else:
            continue

        god.before_phase(phase)

        use_progress_bar = god.config['training']['output']['progress_bar']['batch']
        for xb, yb in tqdm(god.dataloaders[phase]) if use_progress_bar else god.dataloaders[phase]:
            one_batch(god, xb, yb)

        god.after_phase()

    god.after_epoch()

def one_batch(god, xb, yb):
    god.before_batch(xb, yb)

    xb, yb = xb.to(god.device), yb.to(god.device)
    with torch.set_grad_enabled(god.state['phase'] == 'train'):
        pred = god.model(xb)
        loss = god.criterion(pred, yb)
        if god.state['phase'] == 'train':
            god.optimizer.zero_grad()
            loss.backward()
            god.optimizer.step()
            if god.scheduler: god.scheduler.step()

    # todo work around for tuple pred, this likely should just use some class that supports a custom detach method instead of tuple
    god.after_batch(pred.detach().cpu() if type(pred) != tuple else [p.detach().cpu() for p in pred], loss.detach().cpu())