"""Embedded known-plaintext anchors for .spak key recovery.

Auto-generated data -- do not edit by hand. Regenerate by decrypting a
few known-good client installs (of different servers) and taking, per
archive, the first SNIPPET_LEN bytes of the deflate stream of entries
whose uncompressed content (CRC-32) is identical across all of them.
Each anchor is a short 256-byte PREFIX of the raw deflate stream of a
file byte-identical across Seal Online private-server builds, matched to
a target entry by cleartext CRC-32 + size and handed to bkcrack as known
plaintext. Snippets are short fragments only -- never a whole file -- so
no game asset can be reconstructed from them.
"""

# Long base64 snippet literals below exceed the line limit by design.
# ruff: noqa: E501

from __future__ import annotations

import base64
from dataclasses import dataclass

SNIPPET_LEN = 256


@dataclass(frozen=True)
class Anchor:
  archive: str
  name: str
  crc: int
  usize: int
  comp_len: int
  snippet: bytes


def _a(archive, name, crc, usize, comp_len, b64):
  return Anchor(archive, name, crc, usize, comp_len, base64.b64decode(b64))


ANCHORS = [
  _a(
    "actor.spak",
    "E_Dg_a.an1",
    0x4530DEB4,
    15124,
    2073,
    "7Zt/VJRVGsdfJKRkAYUFk45BaqXHVRPUdJr33kBBIEEUCTML5sAAIzAzO6IgQgw/XDDJQyuLteFRLC2wNPCIwsx7b6yr1uphxx+7cGqlPaSV0KbA1ir4Y+fCvPm+zIv3rxzOeXnOmfO+c/nyPdzPc+c+9859YRiGeYQhcSOYYQKWhiYsS01QzQ2ODWVkGTOtLxfb/SO29yEa/XPzHfcnOTzG2a6Tj69STDrTzG6/0KG8e+/ePfIyjhO3Ex1pdxL8Xt1aZ9z/GydYvK8fvZ9yG8T/UIBP/2uh0qv4M6Vr6xdQ6EXTCv1JDOYmIEyny9qYpdZvfLhgRkE4265rPzrG6g==",
  ),
  _a(
    "actor.spak",
    "E_casting_M.an1",
    0x257B1514,
    9504,
    2332,
    "7Vl5UBRXGm8ZEDy5oqjoihpRxAMQVGD6PS7FEMQCjCILjoggKGE4hkFFw6CIB9Sui4i7YswKoq4HqBAl5fR7LkFAUYJkFUGNqATilYghoKhhXw/T0s1R/JVIFX5VXTM0v/n619/vO97rpiiKGkix9tyRokyc50sCA6JloeFrJItmOnrPp672MxtBIqFNtRsbF/Zvp9AIC0uqn5mmCTVAr/2rSH3K6Pz1AnnkbVBlLRX/3tbWxh4OA9rPV5dXgcSD18QsToMcF0Xd4wewrtX+MkPdmDN5bvC0lzGjlWwM41/XIO3nwfB/+4PpZU9zaf41FCI5E7HVDcpKxMzvQcbQdg==",
  ),
  _a(
    "etc.spak",
    "m_hair1.edt",
    0x0DFE0DA9,
    2049,
    2054,
    "AQEI/vcthp7yRiWR0zFo8MsJBzQRrXNDMJbEFX0oOp0AEiEeYkotygdLVNttGxTOCKTLd0FS7I/XV11Eupc5ERrmcqSSTUKxp3VzEo7VO089P0IIZOwAN2veYh38nQBElrvLAliw/PnrZuvMvOGNseK0XvrVF1ZamlgNgPCUMxAXRjlYaaUs7wXQgltQmbW8fUf9GBReVt4M8tx71Z4hlzmJRqTKNweETiVHuXrsCxT0TaUH1zQFgpZ2QqRn3T7bLSMX9c1v/+XkMNnHjb+KZD50v6IvJlVdWfyF+pbXmQOUexIgVKflFjVfScrFH2B9SwuZEkE5MSkiDQ+8xx4IYQ==",
  ),
  _a(
    "etc.spak",
    "p_newevolution_result.edt",
    0x12014FF6,
    2117,
    2122,
    "AUUIuvcpbYRso/AKCvZczQkv9Sj9VGvHcc41TnR5VwyOOX0eailjv3Q1UedroNBS7mAuT2hGGfa567KwuVrvCL5y+kRugJw4nNf1GRnMxgwlQWLj4rcYesyuR15b1kmUEJkidXdmDB4SvUjjdpJaTUl049E9plLj5wS5EX3y4/D+pbH8PocgjY1RsKNk2LV3K0d0yeasvgbrOQ31hDfMaPEadbyF5gJYu5++V4FjfIxOtabuie881Lb992jCGpZBvmrce7C6D6hHDSud2IpuAxHMkVc2RVm+5OzO7ShCnVVzLRq8S1Reuzb0cqVEFCYE9xmOfGh5SL1B9bK7QlexFA==",
  ),
  _a(
    "interface.spak",
    "emblem018.tex",
    0x4B96973F,
    22132,
    2059,
    "7ZxNbBtFFICfvUkaNzjNAasIAjJBFuWnJQJZXCixSCQ4EQvFsYVMYgFJaQXUqqDJocKWOID4CxxyAlHwCQECBSggeojbC72lIoSW/uCkBYQ4xFGreJPW3sebmd2169jx5g/nZ1aK3G/H3p2ZN/PezHtv+vih/fsOvuzu6ht85dVDfe7+/S/2uQ+37nkILF4zAYDjx79MvY6Ic+kcxugzhvnyeqsP0i83/dXQX0eoq2Qd6pt8ZX9Lr0bJkiVLlixZsuRNyVE4DTOgIr6HSZ8vosA2uAnaqLwdQVEcVa+f5LXlHGAUTyOTv98f6opBClDBbRrJ3+H0eKpeP8lryjOoYg==",
  ),
  _a(
    "interface.spak",
    "Mon_hunt.men",
    0x11003F12,
    32304,
    2112,
    "3Z1dbFRFFMdnb1ug5cNGxfAVs4EHNRClWFGQBxGigoCGSkRIXC7b23bD3V3sbhHE+GB4MWB40GhEE16M0sQQ5EWNPhAkUVFQNJGIMb6QaPxMxMSoiXhOZ6Z39vbevR87szvTfzLM7Ozdnu2PmTNf5972ObabfajkFkpOdsu67H0F18nu6SWxtbFcyg2NlKq3VnYPx/9UMmUEO6psiLrRV84I3yNIcyBthLQW0pMxbWwpVQtV10n3BWOqi3jccsVCpVIol1TZaoPULrxuD7uQCVleA2kmpJXwYn9MO83gJrY3zi1XdfbKbnxtdezX02JC29t8uDBup2sGN5THzS4oaw==",
  ),
  _a(
    "item.spak",
    "item_03.ms1",
    0xCA838C2F,
    5618,
    2092,
    "7ZdpUFVHFoCPoOI2iDICsrmwCU8R5YEi73ZHnhJRiShCXDBP2QRJRC1IXFCBlGCUIESREGPcRjHiTLSsxO3dvmomNTFRh0TjUlPloImDmUncK2VFDXO69VJ9eS9VMzXzz3TV6QP34/Q9ffqccxsAgE5C8otyXrNFjYgsmj8Pzj6Hw/ZsPJebx4FJAKZKL6qLs7/Jzc2lujhd5MwZRaRTYeaCnKyiqBHPbzDPPN+jAJMgFZ6OJ21tbU9/KqXgMP7zZ21tqx2e/y/P/rvBfdKl43Pj73tjzqpLl++2DMxaqPZyWaFddUkinHwNhBa7RBj4zStVrDUgjGRsWKI54crdBw==",
  ),
  _a(
    "item.spak",
    "item_02.ms1",
    0x561C4F69,
    7154,
    2221,
    "7Zh7VBXHGcA/XgIKSgxBUJ6KQXyC2nq93J1RMKgBjAa1vqrxgYiioEJUfPAyvCKiIA+pUY6aGA0xGnMSUHY3PlKPxlAFE4wx0VhTekgtxnJSEYKdWV06u8zW9rT/2bnnm4X93e+b2ZnvMXsBAKwUiUuKWbkgKHh4UuxC+OIZbAuetGfy4UkjTgBDst2wKrzvLF26FKvCNXLpkqC4E3Um36CRz+paksW89Gy33xEniIbH7ZdHjx49/isNQ5f279979Ci1y/3/5t5/1uicVNHf1/7fbLKTMm6fPyXtKxdtZyK56PAZNLfeSV7T+goCGIcYLtzJRHKMxxmEf++Eq9vtFQ==",
  ),
  _a(
    "map.spak",
    "water06.tex",
    0x10394138,
    4356,
    2048,
    "pVhfTFvXGfeqTT7FIfF9YJN5mBASwrEDVEIe1bqWh00K09CWB06utRnftFO2eE0ai42NhRIzkkllDG0viErbJCuKKTF16YsX1gxcNcJaQJC93PllDYhKNrFr4027gtLYZ9+Bfd+5kfpQaUYI/XT+fb/f99ecHYr8+OprLQMXR342PHSx5UeRyxdbfv5cZ7fjc37G3Q7HvXtvb90QQhzs7YsM/M0IWHB/3hue/rTA7xfh91vBgc+24TPuLVfqQv54tVU2uhgXlYo4+pxpzbMX/SkTccXn1ILC4Ijl/vi8biB+Q3Nqgy9/QutOWB+vj4QQFz1Z1lHjtN4P9wdFrYY46Q==",
  ),
  _a(
    "map.spak",
    "object_tree_stump_00.ms1",
    0xC45DE12E,
    6908,
    2051,
    "7ZgLUFXHGcf/ImAIRA2oYIQKiPhADFRQUe9uQKNIfALFB0YIcoEiCIGLAj6CgoIWJQaJJtXW6FjFtB2VUiLee461mgkmxmrUpGm0ydiGqo1DiOkk2teeE8+d71w2TmY603QmPTP7neH+Zne/954FAHrpoygr37rMlmErsVozSlcUrcqIiooam1+ci+/IEx0cGZxtzXmmrMD2bavyLT5VnI6cnI+ZMb76O8c5vnYJLZ1MyWQrKywW2fTfM+J/4Dn3HX92CR9MI76ofMfnfla5Pt/8t/9Up28Sq6+PKK2MB+laxdvfP6yE/6nantb3F5a760arKIrmh2K3srvrbrK3Dw==",
  ),
  _a(
    "minimap.spak",
    "m79.edt",
    0x6F5F369B,
    2107,
    2112,
    "ATsIxPcszI/seGLV/lwbCR33NfoYbEbP+Mmb73prV5CZTqCX3vcQngUWjPBdoUTbCywpKOQQLoGorsZCYt9Yzno8jJbpQ4fbAneLZ0jwozS2PefBClFgHIfGoCCAp379xSXl28mweLxtN0+Y/Yaja0jxe/AtyB+Vn193vlyLVCcLs3JANlgBIaa+5QBTX5LMVQJoNAu0eLddGwWkf/O99etSE9Wt4KEmxFId6hGfLAGxry/pu/zCUgeiOVrems8gMUVYf0SCunnNmRLWeojBMLPwKP23WfSbG7xjQYRdpD7tyYHd/GXiiTfDEkxTuA5QzKqyOXHXf3/rBVENBcjoOw==",
  ),
  _a(
    "minimap.spak",
    "npc32.edt",
    0x74CCB01B,
    2109,
    2114,
    "AT0IwvctvuNoKjhe1lsk/bbRlm91BA0DtKONTycbbFit4zoKWH2rYPiQaJOF5GpSqyXl2+xeaeDi5Tra5FwQDR1bTft16TQ0us9gzA4h4Kw7HQHW0828tD+tAYKMp6AnnSh9StzBIVLe+ucLzzxMZxN//eFVaGhi2827szidZ3TJ/zB+F2gL1hxymtZrK6V9YWePsQBqkU+2sYpFp47OxRF0PpXrZ+uauGu01D8scBUHrwqfwJqAKcbjM+7CJBy0CnzqENXs4OhcWHt/y3i1sswpNgT8t59cX86Z3AbbQ3OGfO0c2XLGRkK6mWx/nIn8wzBYofNRj6eeCnmrXpbhzA==",
  ),
  _a(
    "monster.spak",
    "Tamu3pi.an1",
    0x79560FDA,
    5280,
    2048,
    "5ZcLUBRHGscnPEQlcILEFyicluIjIi8Bl+1ueSwPPXMaLooaC5aXQkBgEUGQhRg0uMWJCqgJ6IkRTZAASgV0me6hFEWJCELgjoeoEd8SgmCQ02NvhjAyQ7xK1VXdVSp21TAz3/zp6f5/X/+ml6Ioypji2o8uFGXh9hd5RKxdVKiVi4+Mqn0Dmx7rxCTq58b5wt0HhEZZ21iEW2wKlgdRb2AbO3xe5TwV9r1oAesD3saDGo2GOyq12efAFG5/WgK6DAjN6bS5P7oUZbpoOjz38lNwIqeqgtcvHUNRfeGT4PyvMkGksbZUi5Vy8RTW6Ks/jIMG0YXgQUuh9C02zkqpSg==",
  ),
  _a(
    "monster.spak",
    "T_monhunter_crater_at.ms1",
    0x8957D061,
    7496,
    2048,
    "7Vh7bFRVHj53ptBpO4VCS22RQusDsdAHfTGtnXtEpNZo4uACMfFRS+3DbmmxD6lGpcQXa1Zj1Bho3HWT/cMXf6BoXEvoVdTibmBjSMkaszFFyKpZdAmrBJ/j9505t3PamY5KVIx4bs53zpzvnu/3uzO/3zn3jCWE8KBaomtde3NTb8P6rs62vs7e5u6Gpu5GNMW9rY3iTCiB/KL8S5tbGvs6evtOty+nqyy+P1u6NTo6MN5vaWmRbo3H79+3L/jzePqLLtXRUDot9ktLG5Z3bGhrbFheuvS0OCCmCqVoiR9K0cJQspLQabqt4+bOm5q78SjplqLG5JHabdZG9Oantw==",
  ),
  _a(
    "resource.spak",
    "taget.tex",
    0x7B0AEAB9,
    16644,
    2441,
    "7ZwLUFTXGcevK24wKqFWRFbJIkTEFw/xVcMjixFsEsdHtQZDfCBITCxaXWnShMbE1Khx0k6S6WPSzrSTTidp04kxNQ+pmsRnVBQRFEFAQYgKBWRFWNh7//2+vecCkUVJKrhk7o6/ue5y9577/59zvu875zIkrFuVtiY9YEHqs9YN61IDVq5anRqQER4aGRFAn0xPSVkvJYVHLP3ws4+ykj53HGw4dGbDqiTr8rRUa6g19VlJkjY+JElZWe+XbgLQVAvsAyN951cAYWn3f0mC9s/5xuDd8TvUpI6Ojo6Ojo6Ojo7OncFAeBCexEDCmxhCDCV8XTBU/Hww4UXcSxjFdQ==",
  ),
  _a(
    "resource.spak",
    "stlight2.tex",
    0xA8483601,
    16644,
    2538,
    "7ZzfbxxFEsd3PTuzk514PXjMxhNvxDp2QhIuNj7ihPjiBIOMSSSHOHdO7JwN8TnGseLYgUAE4oWTEBISL0h+Qki84BckizukwElHJE4nXvMI/8H9CfcKXd1d3dU9YzvZsRNH2hJf7ezGOzufquru6h9i5J2F+eWl2l/m3n/3vXfmam8tLM7V7jzf80JfjX0y8O78TO4f/5v64f4/f/3p/r++/+nfP/7/P19PLS7PLyy9eWdhcXHqvx+9lMsNDV068IHruk1Pu+6wC8rVbTWmIXKdy/2G//E3TWH9925YwxrWsIY1rG5znELOcYUKvmsIP887TVL5x/24mc1xnJzreg==",
  ),
  _a(
    "sfx.spak",
    "gd_sword02.tex",
    0xDE31B228,
    4356,
    2049,
    "rZhdbNvWFYAvvWIgkDghKRtWgCXWJe1tQqrEpEQHFiYLFiln87DOEUWKkAUJsEVZcorVU/yjqm3aJZudIMMwYDESbAG2h251gOUt3JohijEMA+rmodgP4WBzW2CPTds9GS22NNu5pBzbTTLbyXhAGxeWznfPzz3nXB+vVsZf+E4gbdWmpqtWoFR53grM9BwJox0+rzEI9fcHs1+s1+uvTFTr/4Lf2Tr8gdmphq1PAN5n4FXN9KP38D/0UvDq8GyzdogWhmXwoh/WTiOEEItYimfddeF0bevnM5ld6n/cmuFphBzHsVmelbCEwydEhbbtUIhnBS7MRYRhUaXz9dovvA==",
  ),
  _a(
    "sfx.spak",
    "t_feroa_flower3.tex",
    0x38C8CC95,
    5748,
    2049,
    "7Zh/TBvXHcC/Zwdm47FYy9yg7Y9dGhGgyK2jDo10+8OoJDSbNhHJB4QieqBkcUK2ebRbb07DHJNMcdNNkSh/TCwTDSAVMInUmlZacxSx3EoGh/bHLtJI41zoEhHM3ZsmVUPtem/fdwcBZemydGPZpH7N2Xz9nv3u874/n2vaDx74/vf4yH7puR+27+e/c/Dwfv5HoUcf387jO088d6AF/rn8OQCgqrOD76dSqZ//4lTqEr5eSq2Of+Yen79TeLw24FXdEHn8buMef/g+v/FTWQfxw7P+N11J8AiCVgHAQQl3hNti6/VND/rm1kVC8Cy3GwB5A9tnu4xJc9F8r4/nKw==",
  ),
  _a(
    "skill.spak",
    "bomb_att_3.ms1",
    0x08E2B40E,
    6613,
    2054,
    "7ZZ/XFPXFcAvIYAIAkUFRK0QVOwqLb+EhLzc+6hMpRZKgrNGkZhUUBwILaDWTpJW8QdMRUUgIJNOUSzS2dmOH0kI0a646vy1trq6DdQpdeCkFYZYML3vhZTk8VD8Z34+Gzef+3n3nHPPvSfv3e851wYAYANGGwCBQT4BPlFJyfLs1Kxnsn+gLDI1Y7VcFhkY9Cz2p9q8Qg9k7mxycnIyMnfq1Jg7ON9i64Uffz53TmRjjwevpG94dv9itD37Rp0G54GxEbdNJ5zIG3f2i7Cospz3GB3gvLgexUxcQr7R8TLEU9CCwqWRzH0epzvrGG+IUfJPzZrj0UT565dX6yl9PQ==",
  ),
  _a(
    "skill.spak",
    "firework_01.ms1",
    0x8BAD8401,
    14638,
    2059,
    "7Zp7bFNVGMDPbXlsyAYiQQgijwjhKV27rd16u1tFp4HghjEDE6UrsuLmXGWUiPjonSYSSHjoqkTFAD5CcBoQIhDb9eKGPOThM27hj2miIFHxMTSCr3q+c++5O72PYgmhZOtHPu4533dOv3Pv/X73O+0uQgj1QyDfcTUPhGqDDaiPimPcjHG31QT8y+tDmV5KxqQ8MkKgeitjz8U6AmsgEBCoclwO2jS9AuUx444fO+bBh1PcglWnOe6KLv1qErstm0tsKkEfHjID0DBE04ZNJTpnBxqJODQY7ccPI5JKHKoJBHzLljfU1y55MOSzFdwcWuLP2CllQjTn3+fig2hTaQ==",
  ),
  _a(
    "wear.spak",
    "W_head_swordman10.ms1",
    0xF3C17F6B,
    3826,
    2048,
    "7VZ5UJRHFv845RAcFEZGGO5DRq5hTFxk+j01IESjElkTCkM4HBESdCBcrhcQFRIl4oUEGBVlkViLoEZgjcz3RcW4KrKaUvFaRYOirloUomKCsm8mGWprq3ar9i/+2O2u35vu3zv69fF1D8dxnJEeS3OykuTBCamLk1SB4eEx3P9amZOUvfiztKR0N095yJSRTmaEyqRiMRpglZqM7ySlp/RNn4e/nPsYjYwsuJSUFDTgPYd2mJGWEbzNUYXNybfBjvzPt7cz/XH6MCE1KTthaY5KLQ8e6UmNRDHSrYzcLYo+ppFOZWSKgmC4Q0YTbsXWAccVIDULfsNvRc/9cykwcA==",
  ),
  _a(
    "wear.spak",
    "R_hammer1.ms1",
    0xB01BF800,
    5210,
    2049,
    "5VcNUFTXFb6LYhCEBIwgROwqIn+6sqD87dt3kIkMmoALBsGhVTCAyE8AhahpdtlgNGj8wZgQrVXTaLWN8d9kEZZ3V1ONKeJftFSjlDoFmwkYE+wYCcXe83YfrISXGdOZppnsztlz3vnu+bn3nnP3PkIIUYiUsiAvq6goZ4lalZ29lPz8PtHKycqnc3KzygvLfuxUfrRP/JueIBEhRjoQz83NBYn6tcY+uensWS0ZwoS+YrIDBzN4WPcoY/+/7RVxi0tC1co5y4qXZH937E9gAv+t/VRGk2wyni+Hxs6BtI4K2Hf+CoeDUc9kM+pe/jpUg89epotRTK6X/HzyYq+QrQ==",
  ),
]
