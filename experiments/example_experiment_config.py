#mattress_00_baseline_config.py

CONFIG =  {
    'name': 'example_experiment',
    'description': 'example config',
    'version': '1.0',
    'dataset': {
        'path': 'datasets/01_mattress_target_only_dataset',
        'type': 'ImageDir',
        'train_path': 'train',
        'val_path': 'val'
    },
    'id2label': {0: 'not_mattress', 1: 'mattress'},
    'label2id': {'not_mattress': 0, 'mattress': 1},
    'model': {
        'name': 'resnet18',
        'classification_type': 'binary',
        'predict_class_function': {'name': 'binary_threshold', 'pred_1_threshold': 0.5}
    },
    'hp': {
        'batch_size': 32,
        'learning_rate': 0.0004,
        'criterion': {
            'name': 'BCELoss'
        },
        'optimizer': {
            'name': 'Adam'
        },
        'scheduler': {
            'name': 'OneCycleLr',
            'max_lr': 0.0004,
            'anneal_strategy': 'cos'
        }
    },
    'sampling': {
        'train': {
            'name': 'undersample'
        },
        'val': {
            'name': 'undersample'
        }
    },
    'data_transforms': {
        'train': [
            {'name': 'SquarePad'},
            {'name': 'Resize', 'size': [224,224]},
            {'name': 'ToTensor'},
            #  {'name': 'Grayscale', 'num_output_channels': 3},
            #  {'name': 'Cutout', 'n_holes': 3, 'length': 100},
            {'name': 'Normalize'}
        ],
        'val': [
            {'name': 'SquarePad'},
            {'name': 'Resize', 'size': [224,224]},
            {'name': 'ToTensor'},
            # {'name': 'Grayscale', 'num_output_channels': 3},
            {'name': 'Normalize'}
        ]
    },
    'training': {
        'n_epochs': 25,
        'val_frequency': 1,
        'metrics': [
            {
                'name': 'accuracy',
                'phase': 'both',
                'get_episode_average': {'phase': 'val'},
                'settings': {},
            },
            {
                'name': 'loss',
                'phase': 'both',
                'settings': {}
            }
        ],
        'output': {
            'save_results': {'path': 'experiments'},
            'progress_bar': {'episode': True, 'epoch': False, 'batch': False},
            'show_metrics': {
                'print': {'episode': True, 'epoch': False, 'batch': False}, 
                'table': True, 
                'plot': False
            }
        }
    },
    'constants': {
        'print_precision': 5,
        'num_workers': 2,
        'x_mean': [0.2064, 0.1979, 0.1849],
        'x_std': [0.316, 0.3042, 0.2883]
    }
}