
#################################################
### THIS FILE WAS AUTOGENERATED! DO NOT EDIT! ###
#################################################
# file to edit: dev_nb/11_train_imagenette.ipynb

from exp.nb_10c import *

def noop(x): return x

class Flatten(nn.Module):
    def forward(self, x): return x.view(x.size(0), -1)

def conv(ni, nf, ks=3, stride=1, bias=False):
    return nn.Conv2d(ni, nf, ks, stride,  padding=ks//2, bias=bias)

act_fn = nn.ReLU(inplace=True)

def init_cnn(m):
    if getattr(m, 'bias', None) is not None: nn.init.constant_(m.bias, 0.)
    if isinstance(m, (nn.Conv2d, nn.Linear)): nn.init.kaiming_normal_(m.weight)
    for l in m.children(): init_cnn(l)

def conv_layer(ni, nf, ks=3, stride=1, zero_bn=False, act=True):
    bn = nn.BatchNorm2d(nf)
    nn.init.constant_(bn.weight, 0. if zero_bn else 1.)
    layers = [conv(ni, nf, ks, stride), bn]
    if act: layers.append(act_fn)
    return nn.Sequential(*layers)

class ResBlock(nn.Module):
    def __init__(self, expansion, ni, nh, stride=1):
        super().__init__()
        nf,ni = nh*expansion,ni*expansion
        layers = [conv_layer(ni, nh, 3, stride),
                  conv_layer(nh, nf, 3, zero_bn=True, act=False)] if expansion == 1 else [
                  conv_layer(ni, nh, 1),
                  conv_layer(nh, nh, 3, stride),
                  conv_layer(nh, nf, 1, zero_bn=true, act=False)
        ]
        self.convs = nn.Sequential(*layers)
        self.idconv = noop if ni==nf else conv_layer(ni, nf, 1, act=False)
        self.pool = noop if stride==1 else nn.AvgPool2d(2, ceil_mode=True)

    def forward(self, x): return act_fn(self.convs(x) + self.idconv(self.pool(x)))

class XResNet(nn.Sequential):
    @classmethod
    def create(cls, expansion, layers, c_in=3, c_out=1000):
        nfs = [c_in, (c_in+1)*8, 64, 64]
        stem = [conv_layer(nfs[i], nfs[i+1], stride=2 if i == 0 else 1) for i in range(3)]

        nfs = [64//expansion,64,128,256,512]
        res_layers = [cls._make_layer(expansion, nfs[i], nfs[i+1], n_blocks=l, stride=1 if i==0 else 2)
                     for i,l in enumerate(layers)]
        res = cls(
            *stem,
            nn.MaxPool2d(kernel_size=3, stride=2, padding=1),
            *res_layers,
            nn.AdaptiveAvgPool2d(1), Flatten(),
            nn.Linear(nfs[-1]*expansion, c_out))
        init_cnn(res)
        return res

    @staticmethod
    def _make_layer(expansion, ni, nf, n_blocks, stride):
        return nn.Sequential(*[ResBlock(expansion, ni if i == 0 else nf, nf, stride if i == 0 else 1) for i in range(n_blocks)])

def xresnet18(**kwargs): return XResNet.create(1, [2, 2, 2, 2], **kwargs)
def xresnet34(**kwargs): return XResNet.create(1, [3, 4, 6, 3], **kwargs)
def xresnet50(**kwargs): return xResNet.create(4, [3, 4, 6, 3], **kwargs)
def xresnet101(**kwargs): return XResNet.create(4, [3, 4, 23, 3], **kwargs)
def xresnet152(**kwargs): return XResNet.create(4, [3, 8, 36, 3], **kwargs)

def get_batch(dl, learn):
    learn.xb, learn.yb = next(iter(dl))
    learn.do_begin_fit(0) # inside is self('begin_fit')
    learn('begin_batch')
    learn('after_fit')
    return learn.xb, learn.yb

def model_summary(learn, data, find_all=False, print_mod=False):
    xb, yb = get_batch(data.valid_dl, learn)
    mods = find_modules(learn.model, is_lin_layer) if find_all else learn.model.children()
    f = lambda hook,mod,inp,out: print(f"===\n{mod}\n" if print_mod else "", out.shape)
    with Hooks(mods, f) as hooks: learn.model(xb)

def create_phases(phases):
    phases = listify(phases)
    return phases + [1 - sum(phases)]

def cnn_learner(arch, data, loss_func, opt_func, lr=1e-2, c_in=None, c_out=None, progress=True, cuda=True, norm=None, mixup=0, xtra_cb=None, **kwargs):
    cbfs = [partial(AvgStatsCallback, accuracy)] + listify(xtra_cb)
    if progress: cbfs.append(ProgressCallback)
    if cuda: cbfs.append(CudaCallback)
    if norm: cbfs.append(partial(BatchTransformXCallback, norm))
    if mixup: cbfs.append(partial(MixUp, mixup))
    arch_args = {}
    if not c_in: c_in = data.c_in
    if not c_out: c_out = data.c_out
    if c_in: arch_args['c_in'] = c_in
    if c_out: arch_args['c_out'] = c_out

    return Learner(arch(**arch_args), data, loss_func, opt_func, lr, cb_funcs=cbfs, **kwargs)