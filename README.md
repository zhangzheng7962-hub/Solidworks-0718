# SOLIDWORKS MCP Server

让 AI（Claude / 其他支持 MCP 的客户端）直接操控 SOLIDWORKS 建模。

```
AI ──MCP协议──► Python MCP 服务 ──COM接口──► SOLIDWORKS
```

你对 AI 说"画一个 100×100×30 的方块",AI 调用本服务的工具,SOLIDWORKS 里就会出现这个零件。

包含 **10 个基础建模工具**:连接、新建零件、草图（矩形/圆/直线/多边形/腰形孔）、特征（拉伸凸台/拉伸切除）。用它们就能搭出绝大多数棱柱类零件。

> 配套图文教程（原理答疑 + API 手册 + 实操项目）见飞书文档《AI 连 SOLIDWORKS 完整指南》。

> ⚠️ **适用版本**：本项目基于 **SOLIDWORKS 2020（中文版）** 开发与实测，兼容 SW 2020 及以上版本（更低版本未验证，部分 API 可能缺失）。

## 环境要求

| 条件 | 说明 |
|------|------|
| Windows 10/11 | COM 接口是 Windows 专属 |
| SOLIDWORKS 2020+ **中文版** | 工具内部使用中文基准面名（前视基准面等） |
| [uv](https://github.com/astral-sh/uv) | Python 包管理器,`pip install uv` 或官网安装。没装 Python 也没关系,uv 会自动处理 |

## 安装（3 步）

### 1. 下载代码

不会 git 的话:点本页右上角绿色 **Code** 按钮 → **Download ZIP** → 解压到任意目录。

会 git 的话:

```bash
git clone https://github.com/zhangzheng7962-hub/Solidworks-0718.git
```

### 2. 安装依赖

在解压/克隆出的目录里打开终端,执行:

```bash
uv sync
```

### 3. 注册到 AI 客户端

**Claude Desktop**:编辑 `%APPDATA%\Claude\claude_desktop_config.json`
**Claude Code**:编辑项目下的 `.mcp.json`

```json
{
  "mcpServers": {
    "solidworks": {
      "command": "uv",
      "args": ["run", "--directory", "C:/你的路径/Solidworks-0718", "solidworks-mcp"]
    }
  }
}
```

> 把 `C:/你的路径/Solidworks-0718` 换成你实际的解压目录,路径用 `/` 或 `\\`。

重启客户端,工具列表里出现 `connect_solidworks` 就成功了。

## 使用

1. **先打开 SOLIDWORKS**（服务是附着到正在运行的 SW 上的）
2. 在对话框里直接说人话,例如:

> 画一个 100×100×30 的方块

AI 会自动拆成工具调用:`new_part` → `create_sketch_on_plane(front)` → `sketch_rectangle(-50,-50,50,50)` → `extrude(30)`,SOLIDWORKS 里就出现这个方块。

### 试试这 3 个入门项目

**方块**:`新建零件 → 前视基准面画 100×100 矩形 → 拉伸 30`
**六角螺母毛坯**:`正六边形(外接圆半径20) → 拉伸10 → 同面画圆(半径10) → 贯穿切除`
**带腰形孔的板**:`矩形 100×60 → 拉伸 10 → 上表面画腰形孔(长30宽10) → 贯穿切除`

## 工具清单（10 个）

| 分类 | 工具 |
|------|------|
| 连接 | `connect_solidworks` |
| 文档 | `new_part` |
| 草图 | `create_sketch_on_plane` `sketch_rectangle` `sketch_circle` `sketch_line` `sketch_polygon` `sketch_slot` |
| 特征 | `extrude` `cut_extrude` |

所有坐标/尺寸单位均为**毫米**,内部自动转换为 SOLIDWORKS API 的米。

## 常见问题

| 现象 | 原因 | 解决 |
|------|------|------|
| 连接失败 | SW 未启动 | 先打开 SOLIDWORKS |
| 无法选择基准面 | 基准面名传错 | 用 `front` / `top` / `right` |
| 没有打开的文档 | 忘了建零件 | 先调 `new_part` |
| 画了草图看不到实体 | 草图只是轮廓 | 草图后必须跟 `extrude`/`cut_extrude` |
| 首次连接较慢 | comtypes 在生成 SW 类型库缓存 | 正常现象,只有第一次慢 |

## 想自己扩展工具?

三步闭环:**录宏找函数名 → chm 手册查参数 → Python(comtypes) 实现**

- 录宏:SW → 工具 → 宏 → 录制,手动操作一遍,函数名就在生成的 VBA 代码里
- 查手册:`<SW安装目录>\SOLIDWORKS\api\sldworksapi.chm`(函数详解)+ `swconst.chm`(常量表),或在线版 [help.solidworks.com](https://help.solidworks.com)
- 实现:参考 `src/solidworks_mcp/tools/` 里现有工具的写法,在注册表中加一项即可

## License & 致谢

MIT License。

项目起步阶段参考了社区开源项目 [alisamsam/solidworks-mcp](https://github.com/alisamsam/solidworks-mcp) 等 SOLIDWORKS MCP 实现,在此致谢。当前代码为独立重写版本:comtypes 强类型绑定、COM STA 单线程串行化、中文版 SW 适配、推理吸附关闭等。
