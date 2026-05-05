---
name: project-reading-coach
description: 先读 README/spec/acceptance 与核心代码，再生成真正面向新人的项目精读文档。主输出必须是 PROJECT_READING_GUIDE.md，而不是 JSON 摘要。
tools: bash, python
---

# 核心目标
本 skill 不是“项目摘要器”，而是“项目精读助手”。

必须解决：
1. 新人读完后知道主链路怎么走。
2. 新人知道每一步该看哪个文件、为什么看。
3. 新人看到字段级样例，而不是变量名。
4. 新人知道框架在这个项目里如何落地。
5. 最终产出可读、可学、可跟着练的 `PROJECT_READING_GUIDE.md`。

# 严格禁止
- 只有摘要、阅读顺序、几个关键词
- “必须先懂：任务状态机 / workflow.execute” 这种空标签
- 只有一行主链路箭头
- demo 退回基础 Python 玩具代码
- 把 JSON 当主产物

# 强制输出
## 1. 一句话结论
## 2. 主链路总图
## 3. 分阶段精读
每阶段都必须有：
- 文件
- 关键函数/类
- 这一段在做什么
- 样例输入
- 样例输出
- 新手先搞懂什么
- 下一步去看哪里

## 4. 关键知识点精讲
必须绑到项目代码。
## 5. 最小调试闭环
## 6. project_demo.py 对照说明
