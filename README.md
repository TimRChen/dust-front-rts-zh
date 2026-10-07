# 《Dust Front RTS》试玩版 简体中文语言包

给 **Dust Front RTS Demo**（Steam AppID `4776100`）**新增一个中文语言选项**，把游戏内全部文本翻译成中文。
游戏自带的语言下拉框里会多出一项 **CHINESE**，选中后整个游戏（菜单、教程、单位/建筑说明、技能、学说、改装件……）都变成中文。

本仓库**不包含任何游戏文件**：补丁脚本读取你自己安装的正版游戏，在本地生成中文语言包。

> 注意：本仓库只是第三方爱好者汉化，与开发方 RtsDimonDev 无关。游戏本体文本版权归原作者所有。

## 效果

| 项目 | 内容 |
| --- | --- |
| 翻译条目 | 689 条（Main 619 / Tutorial 70），覆盖率 100% |
| 语言选项名 | `CHINESE`（与原版 `RUSSIAN` / `ENGLISH` 的命名风格一致） |
| 中文字体 | 无需处理，游戏用动态字体，系统会自动回退到中文字形 |
| 已改动文件 | 仅 `Dust Front RTS_Data/resources.assets`（其余字节完全不动） |
| 是否改动游戏代码 | 否 |

## 安装

需要 Python 3.8+（脚本只用标准库，没有第三方依赖）。

```bash
git clone https://github.com/<你的用户名>/dust-front-rts-zh.git
cd dust-front-rts-zh
python tools/apply.py
```

脚本会自动从 Steam 库（`libraryfolders.vdf`）里找到游戏；找不到时手动指定：

```bash
python tools/apply.py --game-dir "D:\SteamLibrary\steamapps\common\Dust Front RTS Demo"
python tools/apply.py --dry-run      # 只看会做什么，不写文件
```

装完后从 **Steam 启动游戏**，在开始界面底部（或主菜单）的语言下拉框里选 **CHINESE**。
想换回来就选 `ENGLISH` / `RUSSIAN`。

### 卸载 / 还原

```bash
python tools/restore.py
```

脚本会还原安装时自动生成的 `resources.assets.zh-backup`。
如果备份丢了，用 Steam「验证游戏文件完整性」也能恢复原版。

> Steam 更新或验证文件会覆盖补丁，重跑一次 `python tools/apply.py` 即可。

## 原理：为什么只要加一列 CSV

游戏用 Unity 2020.3.3f1 + IL2CPP 打包，自带一套 CSV 本地化系统（`Localizator` / `LocalizedSettings`）。
语言表就是资源文件里的两个 TextAsset：

| TextAsset | 行数 | 内容 |
| --- | --- | --- |
| `Localization_DUST_FRONT - Main` | 619 | 界面、单位、建筑、技能、学说、改装件 |
| `Localization_DUST_FRONT - Tutorial-locals` | 70 | 教程、开场/结束语、成就、提示 |

原始表头是 `Keys,Russian,English`，而**语言下拉框的选项就是由 CSV 的列名生成的**。
所以只要追加一列 `Chinese`，游戏自己就会多出一个中文语言选项——不用改一行代码。

`tools/unitypatch.py` 采用外科手术式写入：把改动后的 TextAsset 重新序列化后追加到文件末尾，
更新对象表中的偏移/长度，然后更新文件头大小。**其余 14000 多个对象一个字节都不动**
（原版与补丁在文件公共部分仅相差 12 字节），因此游戏读到的仍然是一个完全合法的资源文件。

## 目录结构

```
├── translations/zh-CN.json   ← 唯一需要翻译的数据文件（"<csv>/<key>": "中文"）
├── tools/
│   ├── apply.py              安装补丁（找游戏 → 加中文列 → 写回 → 备份）
│   ├── restore.py            还原原版
│   ├── verify.py             校验译文（键覆盖、标签/占位符一致性）
│   ├── unitypatch.py         Unity 序列化文件补丁器（纯标准库）
│   └── dump_source.py        导出原文对照表（仅供本地参考，不要提交）
├── docs/
│   └── CONTRIBUTING.md       参与翻译的方法
└── .github/workflows/ci.yml  提交时自动校验译文
```

## 参与翻译 / 修改译文

1. 编辑 `translations/zh-CN.json`（键是 `main/<key>` 或 `tutorial/<key>`）。
2. 本地校验：

   ```bash
   python tools/verify.py            # 装了游戏会做完整校验，否则只做结构校验
   python tools/apply.py             # 重新应用到游戏里看效果
   ```

翻译时请注意：

* 保留 `<size=25>`、`<color=#FF0000>` 这类富文本标签和 `{0}` 占位符，数量与结构不要变；
* 保留换行结构（多段文本按原段落分行）；
* 术语尽量统一，参考 [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) 里的术语表；
* 要求**符合中文语境的意译**，不要逐字机翻（例如 `Rebels` → 叛军，`TRM "Silach"`（Силач＝大力士）→「大力士」重型抢修车）。

## 已知局限

* **语言项显示为 `CHINESE` 而不是"中文"**：下拉框文字直接取自 CSV 列名，且原版本身就用
  `RUSSIAN` / `ENGLISH` 显示其他语言。列名写成 `Chinese` 还有个好处——中文系统的 Windows
  会按 `SystemLanguage.Chinese` 自动选中它。想改成"中文"字样的话：
  `python tools/apply.py --column 中文`（代价：自动识别失效，需手动选一次）。
* **教程插图里的俄文改不了**：例如部署教程插画上的 `НАЖМИТЕ ПКМ ДЛЯ ОТМЕНЫ` 是烘进贴图的文字，
  不属于文本本地化，需要重绘贴图。
* **主菜单背景上的暗色字母**（如 `MOTOPLACE BUIKA 4/16`）是背景美术元素，英文模式下同样存在。
* 语言偏好保存在注册表 `HKCU\Software\RtsDimonDev\Dust Front RTS\Language_h3872303031`（值为语言序号）。
  删掉它，游戏会回到"按系统语言自动选择"。

## 授权

* 脚本代码：[MIT](LICENSE)
* 译文（`translations/`）：[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.zh)
  —— 允许转载/修改，需署名、非商业、相同方式共享。
* 游戏本体及其原始文本版权归 RtsDimonDev 所有；本仓库不包含这些内容。

如果开发方（RtsDimonDev）希望采用或需要下架本项目，联系后会立即配合。

## 发布到 GitHub

本目录已经是一个初始化好的 git 仓库（`main` 分支，已提交首版）。推送前建议先改成你自己的提交身份：

```bash
cd dust-front-rts-zh
git config user.name  "你的名字"
git config user.email "你的邮箱或 GitHub noreply 邮箱"
git commit --amend --reset-author --no-edit      # 用新身份重写首版提交

# 新建空仓库后（不要在 GitHub 上勾选 README/License，避免冲突）
git remote add origin git@github.com:<你的用户名>/dust-front-rts-zh.git
git push -u origin main
```

> 为什么仓库里没有 `resources.assets`：那是游戏本体文件，分发它等于分发游戏资源。
> 本仓库只包含译文和脚本，安装时由你本机的正版游戏文件在本地生成中文包。
> `.gitignore` 与 CI 都会拦截误提交的游戏文件。

