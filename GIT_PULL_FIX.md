# Git Push 被拒绝的解决方案

## 问题原因

远程仓库（GitHub）包含一些本地没有的提交，通常是因为：
- 创建仓库时勾选了 "Initialize with README"
- 或者远程仓库有其他提交

## 解决方案

### 方案一：合并远程更改（推荐）

```bash
# 1. 拉取远程更改
git pull origin main --allow-unrelated-histories

# 2. 如果有冲突，解决冲突后提交
# （通常会自动合并）

# 3. 推送到远程
git push -u origin main
```

### 方案二：强制推送（如果确定要用本地代码覆盖远程）

⚠️ **警告**：这会覆盖远程仓库的所有内容！

```bash
# 强制推送，覆盖远程仓库
git push -u origin main --force
```

**什么时候用**：
- 远程仓库只有初始化的 README，没有重要内容
- 确定要用本地代码完全替换远程

### 方案三：先拉取再推送（标准流程）

```bash
# 1. 拉取远程更改
git pull origin main --allow-unrelated-histories

# 2. 如果有冲突，Git 会提示
# 编辑冲突文件，解决冲突

# 3. 添加解决后的文件
git add .

# 4. 提交合并
git commit -m "Merge remote-tracking branch 'origin/main'"

# 5. 推送
git push -u origin main
```

---

## 推荐操作（最简单）

如果你刚创建仓库，远程只有 README，建议用**方案二（强制推送）**：

```bash
git push -u origin main --force
```

这样会用你的本地代码覆盖远程的初始 README。

---

## 如果遇到冲突

如果使用方案一后出现冲突：

1. Git 会标记冲突文件
2. 打开冲突文件，找到 `<<<<<<<` 标记
3. 选择保留的代码，删除冲突标记
4. 保存文件
5. `git add .`
6. `git commit -m "Resolve merge conflicts"`
7. `git push -u origin main`
