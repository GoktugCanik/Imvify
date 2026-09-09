"""SRVGGNetCompact architecture, vendored from Real-ESRGAN.

Vendored for the same reason as rrdbnet_arch.py: no basicsr/realesrgan
package dependency, only torch.

Source: https://github.com/xinntao/Real-ESRGAN/blob/master/realesrgan/archs/srvgg_arch.py
Weights: realesr-general-x4v3.pth / realesr-general-wdn-x4v3.pth from
https://github.com/xinntao/Real-ESRGAN (BSD-3-Clause) load directly into
this architecture's state_dict.
"""
import torch
from torch import nn
from torch.nn import functional as F


class SRVGGNetCompact(nn.Module):
    """A compact VGG-style network structure for super-resolution."""

    def __init__(self, num_in_ch=3, num_out_ch=3, num_feat=64, num_conv=32, upscale=4, act_type='prelu'):
        super().__init__()
        self.num_in_ch = num_in_ch
        self.num_out_ch = num_out_ch
        self.num_feat = num_feat
        self.num_conv = num_conv
        self.upscale = upscale
        self.act_type = act_type

        def make_activation():
            if act_type == 'relu':
                return nn.ReLU(inplace=True)
            elif act_type == 'prelu':
                return nn.PReLU(num_parameters=num_feat)
            elif act_type == 'leakyrelu':
                return nn.LeakyReLU(negative_slope=0.1, inplace=True)
            raise ValueError(f'Unsupported act_type: {act_type}')

        self.body = nn.ModuleList()
        self.body.append(nn.Conv2d(num_in_ch, num_feat, 3, 1, 1))
        self.body.append(make_activation())

        for _ in range(num_conv):
            self.body.append(nn.Conv2d(num_feat, num_feat, 3, 1, 1))
            self.body.append(make_activation())

        self.body.append(nn.Conv2d(num_feat, num_out_ch * upscale * upscale, 3, 1, 1))
        self.upsampler = nn.PixelShuffle(upscale)

    def forward(self, x):
        out = x
        for layer in self.body:
            out = layer(out)

        out = self.upsampler(out)
        base = F.interpolate(x, scale_factor=self.upscale, mode='nearest')
        out += base
        return out
