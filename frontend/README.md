# GreenVRP Engine - 企业简约风格前端

## 概述

这是 GreenVRP Engine 的企业简约风格前端界面，基于 Streamlit 构建，采用现代化、简洁的设计理念。

## 设计原则

1. **简洁至上** - 去除冗余元素，突出核心功能
2. **视觉层次** - 清晰的信息架构和视觉层次
3. **企业级配色** - 使用专业、稳重的配色方案
4. **响应式设计** - 适应不同屏幕尺寸
5. **交互友好** - 直观的操作流程和反馈

## 配色方案

| 颜色名称 | 色值 | 用途 |
|---------|------|------|
| Primary | #2C3E50 | 主色调，用于标题、重要文本 |
| Secondary | #34495E | 次要色调 |
| Accent | #3498DB | 强调色，用于按钮、链接 |
| Success | #27AE60 | 成功状态 |
| Warning | #F39C12 | 警告状态 |
| Danger | #E74C3C | 错误状态 |
| Light | #ECF0F1 | 背景色 |
| White | #FFFFFF | 卡片背景 |

## 目录结构

```
frontend/
├── app.py                 # 主应用文件
├── config.py             # 配置文件
├── components/           # 组件目录
│   ├── __init__.py      # 组件初始化
│   ├── map_view.py      # 地图组件
│   └── chart_view.py    # 图表组件
└── README.md            # 本文件
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动应用

使用项目根目录的启动脚本：

```bash
python start_enterprise_ui.py
```

或直接使用 Streamlit：

```bash
streamlit run frontend/app.py
```

### 3. 访问应用

打开浏览器访问 `http://localhost:8501`

## 主要功能

### 1. 仪表板 (📊 Dashboard)
- 实时状态监控
- 快速操作入口
- 关键指标展示
- 求解进度跟踪

### 2. 路线规划 (🗺️ Route Planning)
- 交互式地图可视化
- 路线统计信息
- 详细路线数据
- 车辆轨迹展示

### 3. 成本分析 (💰 Cost Analysis)
- 五维成本核算
- 成本结构分析
- 碳排放分析
- 效率指标评估

### 4. 对比分析 (📈 Comparison Analysis)
- 多方案对比
- 性能指标对比
- 碳排放对比
- 最佳方案推荐

## 组件说明

### 地图组件 (map_view.py)

- `create_enterprise_map()` - 创建企业风格地图
- `display_route_statistics()` - 显示路线统计
- `display_route_details()` - 显示路线详情

### 图表组件 (chart_view.py)

- `create_cost_breakdown_chart()` - 成本分解饼图
- `create_cost_comparison_chart()` - 成本对比柱状图
- `create_performance_comparison_chart()` - 性能对比图
- `create_carbon_emission_chart()` - 碳排放对比图
- `create_vehicle_utilization_chart()` - 车辆利用率图
- `create_time_analysis_chart()` - 时间分析图
- `create_efficiency_indicators()` - 效率指标图
- `enterprise_metric_row()` - 企业风格指标行

## 配置说明

### 全局配置 (config.py)

- `ENTERPRISE_COLORS` - 配色方案
- `DEFAULT_PARAMS` - 默认参数
- `DEFAULT_VEHICLE_CONFIG` - 车辆配置
- `STRATEGY_CONFIG` - 求解策略配置
- `MAP_CONFIG` - 地图配置

### 页面配置

通过 `st.set_page_config()` 设置：
- `page_title` - 页面标题
- `page_icon` - 页面图标
- `layout` - 布局方式
- `initial_sidebar_state` - 侧边栏初始状态

## 自定义样式

### CSS 类名

- `.enterprise-header` - 主标题
- `.enterprise-title` - 标题文本
- `.enterprise-subtitle` - 副标题
- `.metric-card` - 指标卡片
- `.metric-title` - 指标标题
- `.metric-value` - 指标数值
- `.section-header` - 章节标题
- `.status-badge` - 状态标签

### 使用示例

```python
st.markdown("""
<div class="metric-card">
    <div class="metric-title">总成本指标</div>
    <div class="metric-value">¥1,234,567</div>
</div>
""", unsafe_allow_html=True)
```

## 性能优化

1. **数据缓存** - 使用 `@st.cache_data` 装饰器
2. **惰性加载** - 组件按需加载
3. **图表优化** - 限制数据点数量
4. **地图优化** - 使用地图瓦片缓存

## 浏览器兼容性

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## 注意事项

1. 确保 Python 版本 >= 3.8
2. 确保 Streamlit 版本 >= 1.20.0
3. 确保项目依赖已正确安装
4. 建议使用 Chrome 浏览器获得最佳体验

## 开发指南

### 添加新组件

1. 在 `components/` 目录下创建新文件
2. 在 `components/__init__.py` 中导出
3. 在主应用中导入使用

### 修改样式

1. 编辑 `load_enterprise_styles()` 函数
2. 使用 CSS 类名保持一致性
3. 遵循配色方案

### 添加新页面

1. 在主应用中添加新的 tab
2. 创建对应的渲染函数
3. 添加必要的导航元素

## 版本历史

- v1.0.0 - 初始版本
  - 企业简约风格设计
  - 核心功能实现
  - 响应式布局

## 联系方式

如有问题或建议，请联系项目维护团队。

## 许可证

Copyright © 2024 GreenVRP Engine
