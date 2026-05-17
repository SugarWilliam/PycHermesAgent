# WBS数据JSON Schema

生成脚本 `generate_wbs.py` 的输入数据格式。

## 完整结构

```json
{
  "project_name": "NT98533-C17-6MP-stitch单机",
  "version": "V1.0",
  "date": "20260410",
  "group_name": "电源二组WBS模板",
  "department": "研发中心-嵌入式-电源产品二组",
  "members": "@产品-张三@项目-李四@嵌入式-王五@硬件-赵六@测试-钱七",
  "wechat_group": "C17V1-P/C17V2-W项目交流群",
  "project_status": "RUNNING",
  "priority": "S级",
  "branch": "V29.3",
  "wepan_path": "研发共享\\产品资料及研发过程数据（秘密级）\\...",
  "spec_doc": "产品规格表名称",
  "constraints": "V1.0 开发阶段WBS，V2.0 基线WBS, V3.0 维护WBS ，WBS一周最少迭代一次",
  "board_type_ref": "Board_Type 命名规则对照表 V2.0",
  "spec_summary_ref": "产品规格汇总",
  "hardware_notes": "硬件单元测试版本默认参数...(可选)",
  "sections": [
    {
      "name": "里程碑与版本计划",
      "tasks": [
        {
          "name": "方案评估",
          "assignee": "@嵌入式-王五",
          "status": "待启动",
          "deadline": "2026.04.01",
          "notes": "【要求】编码性能+AI性能+DDR带宽..."
        }
      ]
    }
  ]
}
```

## 字段说明

### 顶层字段

| 字段 | 必填 | 说明 |
|------|------|------|
| project_name | 是 | 项目名称，如 "NT98533-C17-6MP-stitch单机" |
| version | 否 | WBS版本，默认 "V1.0" |
| date | 否 | 日期标识，默认当天 YYYYMMDD |
| group_name | 否 | 组别名称，默认 "WBS模板" |
| department | 是 | 部门全称 |
| members | 是 | 项目成员，格式 `@角色-姓名` |
| wechat_group | 否 | 微信群组名称 |
| project_status | 否 | 默认 "RUNNING" |
| priority | 否 | S/A/B/C级，默认 "S级" |
| branch | 否 | 工作分支 |
| sections | 是 | 分区列表 |

### Section对象

| 字段 | 必填 | 说明 |
|------|------|------|
| name | 是 | 分区名称 |
| tasks | 是 | 任务列表 |

### Task对象

| 字段 | 必填 | 说明 |
|------|------|------|
| name | 是 | 任务名称 |
| assignee | 否 | 负责人，格式 `@角色-姓名` |
| status | 否 | 待启动/进行中/已完成/取消，默认"待启动" |
| deadline | 否 | 预计结束时间 YYYY.MM.DD |
| notes | 否 | 备注说明 |

### resource_performance对象（可选）

用于生成"资源与性能"sheet页，各字段均可选，有默认值。

| 字段 | 说明 | 默认值 |
|------|------|--------|
| ddr_items | DDR区块的条目列表 | ["DDR满负载带宽", "DDR内存分布", "满负载内存media余量", "满负载内存OS余量"] |
| npu_title | NPU区块标题 | "NPU 使用率" |
| npu_subtitle | NPU区块副标题 | "{project_name} AI性能测试" |
| npu_items | NPU区块的条目列表 | ["CNN频率"] |
| ai_scenario | AI工作负载场景描述 | ""（根据项目AI功能自动生成） |
| flash_items | FLASH区块的条目列表 | ["rootfs 镜像格式、压缩方式", "rootfs分区余量", "app 镜像格式、压缩方式", "app分区余量", "downloade 分区大小和余量"] |
| cpu_items | CPU区块的条目列表 | ["满负载CPU使用率"] |

示例：
```json
{
  "resource_performance": {
    "npu_subtitle": "533 AI性能测试",
    "ai_scenario": "ppvd@10fps + clip@2fps + AI isp@15fps + AI cds + AI Ns"
  }
}
```

## 常见分区名称

以下是模板中常见的分区名称（可根据项目需要增删）：

1. 里程碑与版本计划
2. 变更记录
3. 产品
4. 媒体驱动
5. 图像相关
6. 业务适配
7. 新增业务适配
8. 研发和测试
9. 风险、关键路径、重点问题
