import torch
import torch.optim as optim
import torch.utils.data
import torch.backends.cudnn as cudnn
import torchvision
from torchvision import transforms, datasets
import numpy as np
import matplotlib.pyplot as plt
import time
import tensorboardX
import pandas as pd

import model
import utils

from efficientnet_pytorch import EfficientNet

import os

from tensorboardX import SummaryWriter

import torchvision.models

class Arg():
    def __init__(self,
                 project_name='test',
                 class_num=62,
                 input_size=(64, 64),
                 lr=0.01,
                 epoch=100,
                 cuda='cuda',
                 train_root='../traffic/data/train',
                 train_batch_size=16,
                 val_root='../traffic/data/val',
                 val_batch_size=16,
                 load='make_model',
                 model_type='ResNet18',
                 model_save_dir='./model_save',
                 model_load_dir='./model_save/traffic_DesenNet_224x224_16.ckp.params.pth',
                 log_dir='./logs',
                 save_mode='save_params',
                 checkpoint_per_epoch=5,
                 using_tensorboardx=True,
                 tensorboardx_file='./logs',
                 verbose=0
                 ):
        self.project_name = project_name
        self.class_num = class_num
        self.input_size = input_size
        self.lr = lr
        self.epoch = epoch
        self.cuda = cuda
        self.train_root = train_root
        self.train_batch_size = train_batch_size
        self.val_batch_size = val_batch_size
        self.val_root = val_root
        self.load = load
        self.model_type = model_type
        self.model_save_dir = model_save_dir
        self.model_load_dir = model_load_dir
        self.log_dir = log_dir
        self.verbose = verbose
        self.save_mode = save_mode
        self.checkpoint_per_epoch = checkpoint_per_epoch
        self.using_tensorboardx = using_tensorboardx
        self.tensorboardx_file = tensorboardx_file

class Net(object):
    def __init__(self, args):

        self.project_name = args.project_name

        self.class_num = args.class_num

        self.input_size = args.input_size

        self.model = None

        self.lr = args.lr
        self.epochs = args.epoch
        self.total_epochs = 0

        self.criterion = None
        self.optimizer = None
        self.scheduler = None

        self.device = torch.device('cpu')
        self.cuda = args.cuda
        if self.cuda == 'cuda':
            self.device = torch.device('cuda')
        else:
            self.device = torch.device('cpu')

        self.train_root = args.train_root
        self.train_batch_size = args.train_batch_size
        self.train_loader = None

        self.val_root = args.val_root
        self.val_batch_size = args.val_batch_size
        self.val_loader = None

        self.load = args.load
        self.model_type = args.model_type
        self.model_save_dir = os.path.join(
            args.model_save_dir, args.project_name)
        self.model_load_dir = args.model_load_dir
        self.log_dir = os.path.join(args.log_dir, args.project_name)

        self.verbose = args.verbose

        self.loss = 0
        self.acc = 0.0
        self.val_loss = 0
        self.val_acc = 0.0

        self.logger_file_path = self.log_dir + '.log'
        self.logger = utils.creat_logger(self.logger_file_path)

        self.checkpoint_data_struct = None

        self.save_mode = args.save_mode

        self.checkpoint_per_epoch = args.checkpoint_per_epoch

        self.using_tensorboardx = args.using_tensorboardx

        if self.using_tensorboardx == True:
            self.tensorboardx_file = os.path.join(
                args.tensorboardx_file, args.project_name)
            self.tb_writer = SummaryWriter(
                self.tensorboardx_file, comment=self.model_type)
        else:
            self.tb_writer = None
            self.tensorboardx_file = None

        self.train_sample_size = 0
        self.val_sample_size = 0

        self.best_params = None

        self.params_num = 0

    def _make_model(self):
        if self.model_type == 'LeNet':
            self.model = model.LeNet(self.input_size,self.class_num).to(self.device)
            self.optimizer = optim.SGD(
                self.model.parameters(), lr=self.lr, momentum=0.9)
            # self.scheduler = optim.lr_scheduler.StepLR(
            #     self.optimizer,step_size = 25, gamma=0.5,last_epoch = -1)
            self.scheduler = optim.lr_scheduler.CosineAnnealingLR(
                self.optimizer,T_max = 60,last_epoch = -1)
            self.criterion = torch.nn.CrossEntropyLoss().to(self.device)

        elif self.model_type == 'ResNet18':
            self.model =  torchvision.models.ResNet(torchvision.models.resnet.BasicBlock,[2,2,2,2],self.class_num).to(self.device)
            self.optimizer = optim.SGD(
                self.model.parameters(), lr=self.lr, momentum=0.9)
            self.scheduler = optim.lr_scheduler.CosineAnnealingLR(
                self.optimizer,T_max = 60,last_epoch = -1)
            self.criterion = torch.nn.CrossEntropyLoss().to(self.device)

        elif self.model_type == 'ResNet34':
            self.model =  torchvision.models.ResNet(torchvision.models.resnet.BasicBlock,[3, 4, 6, 3],self.class_num).to(self.device)
            self.optimizer = optim.SGD(
                self.model.parameters(), lr=self.lr, momentum=0.9)
            self.scheduler = optim.lr_scheduler.CosineAnnealingLR(
                self.optimizer,T_max = 60,last_epoch = -1)
            self.criterion = torch.nn.CrossEntropyLoss().to(self.device)   

        elif self.model_type == 'EfficientNetb0':
            self.model = EfficientNet.from_name('efficientnet-b0').to(self.device)
            self.optimizer = optim.SGD(
                self.model.parameters(), lr=self.lr, momentum=0.9)
            self.scheduler = optim.lr_scheduler.CosineAnnealingLR(
                self.optimizer,T_max = 60,last_epoch = -1)
            self.criterion = torch.nn.CrossEntropyLoss().to(self.device)
        
        elif self.model_type == 'DesenNet':
            self.model = torchvision.models.DenseNet(num_classes=self.class_num).to(self.device)
            self.optimizer = optim.SGD(
                self.model.parameters(), lr=self.lr, momentum=0.9)
            self.scheduler = optim.lr_scheduler.CosineAnnealingLR(
                self.optimizer,T_max = 60,last_epoch = -1)
            self.criterion = torch.nn.CrossEntropyLoss().to(self.device) 

        elif self.model_type == 'VGG19bn':
            cfg = [64, 64, 'M', 128, 128, 'M', 256, 256, 256, 256, 'M', 512, 512, 512, 512, 'M', 512, 512, 512, 512, 'M']
            features = torchvision.models.vgg.make_layers(cfg,batch_norm = True)
            self.model = torchvision.models.VGG(features = features,num_classes=self.class_num).to(self.device)
            self.optimizer = optim.SGD(
                self.model.parameters(), lr=self.lr, momentum=0.9)
            self.scheduler = optim.lr_scheduler.CosineAnnealingLR(
                self.optimizer,T_max = 60,last_epoch = -1)
            self.criterion = torch.nn.CrossEntropyLoss().to(self.device) 
        elif self.model_type == 'VGG11':
            cfg =  [64, 'M', 128, 'M', 256, 256, 'M', 512, 512, 'M', 512, 512, 'M']
            features = torchvision.models.vgg.make_layers(cfg,batch_norm = False)
            self.model = torchvision.models.VGG(features = features,num_classes=self.class_num).to(self.device)
            self.optimizer = optim.SGD(
                self.model.parameters(), lr=self.lr, momentum=0.9)
            self.scheduler = optim.lr_scheduler.CosineAnnealingLR(
                self.optimizer,T_max = 60,last_epoch = -1)
            self.criterion = torch.nn.CrossEntropyLoss().to(self.device)
        elif self.model_type == 'VGG11bn':
            cfg =  [64, 'M', 128, 'M', 256, 256, 'M', 512, 512, 'M', 512, 512, 'M']
            features = torchvision.models.vgg.make_layers(cfg,batch_norm = True)
            self.model = torchvision.models.VGG(features = features,num_classes=self.class_num).to(self.device)
            self.optimizer = optim.SGD(
                self.model.parameters(), lr=self.lr, momentum=0.9)
            self.scheduler = optim.lr_scheduler.CosineAnnealingLR(
                self.optimizer,T_max = 60,last_epoch = -1)
            self.criterion = torch.nn.CrossEntropyLoss().to(self.device)   
        elif self.model_type == 'AlexNet':
            self.model = torchvision.models.AlexNet(num_classes = self.class_num).to(self.device)
            self.optimizer = optim.SGD(
                self.model.parameters(), lr=self.lr, momentum=0.9)
            self.scheduler = optim.lr_scheduler.CosineAnnealingLR(
                self.optimizer,T_max = 60,last_epoch = -1)
            self.criterion = torch.nn.CrossEntropyLoss().to(self.device)            

    def load_model(self):
        if self.load == 'load_model':
            self.model = torch.load(self.model_load_dir).to(self.device)
        elif self.load == 'load_params':
            self._make_model()
            checkpoint_data = torch.load(self.model_load_dir)
            self.model.load_state_dict(checkpoint_data['model_state_dict'])
            self.optimizer.load_state_dict(
                checkpoint_data['optimizer_state_dict'])
            self.scheduler.load_state_dict(checkpoint_data['scheduler_state_dict'])
            self.total_epochs = checkpoint_data['total_epoch']
            print(self.total_epochs)
        elif self.load == 'make_model':
            self._make_model()
        self.params_num = sum([param.nelement() for param in self.model.parameters()])/1e6
        print(self.model)
        print("number of params:%2.fM"%self.params_num)

    def load_data(self):

        train_transform = transforms.Compose([transforms.Resize(self.input_size),
                                              transforms.RandomVerticalFlip(),
                                              transforms.RandomHorizontalFlip(),
                                              transforms.RandomRotation((-1,45)),
                                              transforms.ToTensor(),
                                              transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                                                   std=[0.229, 0.224, 0.225])])

        train_datasets = datasets.ImageFolder(self.train_root, train_transform)
        self.train_loader = torch.utils.data.DataLoader(
            train_datasets, batch_size=self.train_batch_size, shuffle=True, num_workers=8)

        val_transform = transforms.Compose([transforms.Resize(self.input_size),
                                            transforms.ToTensor(),
                                            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                                                 std=[0.229, 0.224, 0.225])])

        val_datasets = datasets.ImageFolder(self.val_root, val_transform)
        self.val_loader = torch.utils.data.DataLoader(
            val_datasets, batch_size=self.val_batch_size, shuffle=False, num_workers=8)

        self.train_sample_size = len(self.train_loader)
        self.val_sample_size = len(self.val_loader)

    def train(self):
        if self.verbose == 1:
            print("train:")
        self.model.train()

        train_loss = 0
        train_correct = 0
        total = 0

        for batch_num, (data, target) in enumerate(self.train_loader):
            data, target = data.to(self.device), target.to(self.device)
            self.optimizer.zero_grad()
            output = self.model(data)
            loss = self.criterion(output, target)
            loss.backward()
            self.optimizer.step()
            train_loss += loss.item()
            prediction = torch.max(output, 1)
            total += target.size(0)

            train_correct += np.sum(prediction[1].cpu().numpy()
                                    == target.cpu().numpy())
            if self.verbose == 1:
                utils.progress_bar(batch_num, len(self.train_loader), 'Loss: %.4f | Acc: %.3f%% (%d/%d)'
                                   % (train_loss / (batch_num + 1), 100. * train_correct / total, train_correct, total))

        return 100 * train_loss / total, train_correct / total

    def val(self):
        if self.verbose == 1:
            print('val:')
        self.model.eval()
        val_loss = 0
        val_correct = 0
        total = 0

        with torch.no_grad():
            for batch_num, (data, target) in enumerate(self.val_loader):
                data, target = data.to(self.device), target.to(self.device)
                output = self.model(data)
                loss = self.criterion(output, target)
                val_loss += loss.item()
                prediction = torch.max(output, 1)
                total += target.size(0)
                val_correct += np.sum(prediction[1].cpu().numpy()
                                      == target.cpu().numpy())
                if self.verbose == 1:
                    utils.progress_bar(batch_num, len(self.val_loader), 'Loss: %.4f | Acc: %.3f%% (%d/%d)'
                                       % (val_loss / (batch_num + 1), 100. * val_correct / total, val_correct, total))

        return 100 * val_loss/total, val_correct / total

    def save(self):
        if self.save_mode == 'save_model':
            torch.save(self.model, self.model_save_dir + '.model.pth')
        elif self.save_mode == 'save_params':
            torch.save(self.model, self.model_save_dir + '.params.pth')

        torch.save(self.best_params,
                   self.model_save_dir + '.best.params.pth')

    def run(self):
        self.load_data()
        self.load_model()
        train_info = ()
        train_info = (" %s | train set size:%dx%d | val set size:%dx%d | input size:%s | class num:%d | lr: %f" 
        % (self.model_type,self.train_sample_size,self.train_batch_size,self.val_sample_size,self.val_batch_size, str(self.input_size),self.class_num,self.lr))
        self.logger.debug(train_info)

        accuracy = 0
        for epoch in range(1, self.epochs + 1):

            epoch_time = time.time()

            self.scheduler.step(epoch)

            self.loss, self.acc = self.train()

            self.val_loss, self.val_acc = self.val()
            if self.val_acc > accuracy:
                accuracy = self.val_acc
                self.best_params = {
                    'total_epoch': self.total_epochs,
                    'model_state_dict': self.model.state_dict(),
                    'optimizer_state_dict': self.optimizer.state_dict(),
                    'scheduler_state_dict':self.scheduler.state_dict(),
                    'loss': self.loss,
                    'acc': self.acc,
                    'val_loss': self.val_loss,
                    'val_acc': self.val_acc,
                    'model_type': self.model_type
                }
                

            self.total_epochs = self.total_epochs + 1

            epoch_time = time.time() - epoch_time
            epoch_time = utils.format_time(epoch_time)
            info = self.model_type
            info += (" | epoch:%d/%d | tol_epoch:%d | loss:%.4f | acc:%5.1f%% | val_loss:%.4f | val_acc:%.4f%% | lr:%f | time: %s"
                     % (epoch, self.epochs, self.total_epochs, self.loss, 100.0*self.acc, self.val_loss, 100.0*self.val_acc,self.scheduler.get_lr()[0] ,epoch_time))
            self.logger.info(info)

            if epoch % self.checkpoint_per_epoch == 0:
                print("checkpoint.....")
                self.checkpoint()
                print("checkpoint success.")

            if self.using_tensorboardx == True:
                self.tb_write()

            # print(self.model_type, "| epoch:%d/%d | loss:%.4f | acc:%5.1f%%" % (epoch, self.epochs, self.loss, 100.0*self.acc),
            #           "| val_loss:%.4f | val_acc:%.4f%% | time:" % (self.val_loss, 100.0*self.val_acc), epoch_time)

            if epoch == self.epochs:
                print("===> BEST ACC. PERFORMANCE:%.3f%%" %
                      (accuracy * 100))
                self.save()
        self.tb_writer.close()

    def checkpoint(self):

        self.checkpoint_data_struct = {
            'total_epoch': self.total_epochs,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'scheduler_state_dict':self.scheduler.state_dict(),
            'loss': self.loss,
            'acc': self.acc,
            'val_loss': self.val_loss,
            'val_acc': self.val_acc,
            'model_type': self.model_type
        }

        torch.save(self.checkpoint_data_struct,
                   self.model_save_dir + '.ckp.params.pth')

        torch.save(self.best_params,
                   self.model_save_dir + '.best.ckp.params.pth')

    def imshow(self):
        inputs, classes = next(iter(self.train_loader))
        inp = torchvision.utils.make_grid(inputs)

        inp = inp.numpy().transpose((1, 2, 0))
        mean = np.array([0.485, 0.456, 0.406])
        std = np.array([0.229, 0.224, 0.225])
        inp = std * inp + mean
        inp = np.clip(inp, 0, 1)
        plt.imshow(inp)
        plt.pause(0.001)
        input()

    def tb_write(self):
        self.tb_writer.add_scalars(
            'loss/epochs', {'train_loss': self.loss, 'val_loss': self.val_loss}, self.total_epochs)

        self.tb_writer.add_scalars(
            'acc/epochs', {'train_acc': self.acc, 'val_acc': self.val_acc}, self.total_epochs)


if __name__ == "__main__":
    args = Arg()
    net = Net(args)
    net.run()
    # net.load_data()
