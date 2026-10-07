# 参与翻译

## 文件

所有译文都在 [`translations/zh-CN.json`](../translations/zh-CN.json)，格式很简单：

```json
{
 "__language__": "zh-CN",
 "main/play": "开始游戏",
 "tutorial/tutorial-deploy-0": "这就是你选定的部队。需要把他们部署到战场上才能开始战斗。"
}
```

* 键名 = `<csv>/<key>`，`<csv>` 只能是 `main` 或 `tutorial`；键名**不要改**，它对应游戏里的文本位。
* 以 `__` 开头的键是元数据，不是文本。

## 想看到原文？

在装了游戏的机器上运行：

```bash
python tools/dump_source.py
```

会生成 `source-reference.csv`（含俄文/英文原文，已被 .gitignore 忽略，**不要提交**）。

## 提交前自检

```bash
python tools/verify.py
```

* 装了游戏：会逐条比对你写的译文和游戏里的原文（标签、占位符、键覆盖）。
* 没装游戏：也会做结构校验（JSON 格式、标签配对、`{0}` 占位符、是否含中文等）。

CI 也会跑一遍同样的校验。

## 翻译规范

1. **意译优先**。按中文军事/游戏语境重写，不要逐字硬套。
   * `Start`（战役入口）→ 启动；`Play` → 开始游戏
   * `Rebels` → 叛军；`Mutants` → 变异体；`Robotic Escalation` → 机械升格
   * `BREM`（俄军装甲抢修车）→ BREM 抢修车；`TRM "Silach"`（Силач＝大力士）→「大力士」重型抢修车
2. **格式标记必须原样保留**：`<size=25>`、`<color=#FF7078>`、`</color>`、`{0}` 等，
   数量、配对、位置都要对上（`verify.py` 会检查）。
3. **换行结构保留**：多段文本按原段落分行；列表项各行独立。
4. **术语统一**，见下表；新增术语请先加进表里再使用。

## 术语表（节选）

| 原文 | 中文 | 说明 |
| --- | --- | --- |
| Materials | 材料 | 主要资源 |
| Supply | 补给 | 部队上限 |
| Parts | 零件 | 科技资源 |
| Energy / network power | 电力 | 电网负荷 |
| Doctrine | 学说 | 全局升级 |
| Local equipment / local upgrade | 本机装备 | 单位改装 |
| Strike group | 打击群 | |
| Hit points | 生命值 | |
| Pure damage | 纯粹伤害 | 无视护甲的伤害类型 |
| MCV | MCV 机动建造车 | 保留缩写 |
| BREM | BREM 抢修车 | 保留缩写 |
| Rebels | 叛军 | |
| Mutants | 变异体 | |
| Robotic Escalation | 机械升格 | 阵营名 |
| Mercenaries | 雇佣兵 | |
| Fourth Industrial Empire | 第四工业帝国 | |
| Complector | 组装体 | 变异体生物工程站 |
| Brutes | 蛮兵 | |
| Dreadnought | 无畏级 | |
| MLRS "Vortex" | 「旋涡」多管火箭炮 | |
| Howitzer "Molot" | 「铁锤」榴弹炮 | |
| Combines | 采集车 | |
