# API 规范文档

本文档定义后端 API 的设计规则、权限边界、响应结构和第一版接口规划。后续新增或修改接口前，必须先阅读本文档。

API 的目标不是只满足某一个页面，而是沉淀可复用的业务能力，让后台管理、后台查询、员工报工和员工查询都能稳定迭代。

## 一、基本原则

- API 统一由 FastAPI 提供。
- 业务接口统一使用 `/api` 前缀。
- 健康检查接口可以不使用 `/api` 前缀。
- 接口命名围绕业务资源，不围绕页面名称。
- 后端必须负责权限校验、数据校验、工资计算和数据库写入。
- 前端只负责展示、交互和调用 API。
- 同一个业务能力只能有一套主要 API，页面之间必须优先复用。
- 新增接口必须同步登记到本文档。

## 二、命名规则

推荐：

```text
GET /api/me
GET /api/admin/accounts
GET /api/admin/processes
GET /api/employee/work-reports
POST /api/employee/work-reports
GET /api/admin/work-report-summary
```

不推荐：

```text
GET /api/admin-query-page-data
GET /api/get-user-list-for-table
POST /api/save-employee-page-form
```

规则：

- 名词用复数资源名，例如 `accounts`、`processes`、`work-reports`。
- 查询使用 `GET`。
- 新增使用 `POST`。
- 整体替换使用 `PUT`。
- 局部修改使用 `PATCH`。
- 物理删除使用 `DELETE`，且第一版仅超级权限可用。
- 停用、确认等业务动作优先使用明确子路径，例如 `/disable`、`/confirm`。

## 三、权限规则

所有业务接口都必须在后端做登录态和权限校验。

- 未登录用户不能访问业务接口。
- 员工只能访问自己的数据。
- 普通管理员只能访问自己权限范围内的员工数据。
- 超级权限可以访问全局数据。
- 普通管理员不能物理删除账号或工序。
- 超级权限物理删除账号或工序时，后端必须保证不破坏历史报工和历史工资归档。
- 前端隐藏按钮不等于权限控制，后端必须再次校验。

员工端正式接口不应由前端传 `account_id` 决定操作谁。后端应从登录态识别当前员工。

推荐：

```text
GET /api/employee/work-report-history
POST /api/employee/work-reports
```

不推荐作为正式接口：

```text
GET /api/work-report-history/{account_id}
PUT /api/work-reports/{account_id}
```

后者可以作为当前演示阶段过渡接口，但后续必须收敛。

## 四、响应结构

第一版可以继续兼容当前前端已有返回结构，但新增正式接口建议统一响应格式。

单条数据：

```json
{
  "data": {},
  "message": "ok"
}
```

列表数据：

```json
{
  "data": [],
  "total": 0,
  "message": "ok"
}
```

分页数据：

```json
{
  "data": [],
  "page": 1,
  "pageSize": 20,
  "total": 0,
  "message": "ok"
}
```

错误响应可以使用 FastAPI 默认结构：

```json
{
  "detail": "错误原因"
}
```

同类业务错误的 `detail` 文案应保持一致，前端不能依赖不稳定的错误文本做复杂判断。

## 五、字段命名规则

第一版前端当前已使用 camelCase 字段，例如 `managerId`、`processIds`、`workDate`。后续新增正式响应优先保持前端友好的 camelCase。

数据库字段可以使用 snake_case，例如 `manager_id`、`process_id`、`work_date`。

规则：

- API 请求体如果已存在 snake_case，可在过渡期保留。
- 新增正式接口建议统一 camelCase 请求和响应。
- 同一个接口内不要混用同一字段的两种名字。
- 字段变更必须先兼容旧前端，再逐步清理。

## 六、已有健康检查接口

### `GET /health`

用途：检查后端服务是否启动。

权限：不需要登录。

返回示例：

```json
{
  "status": "ok",
  "app": "employee-work-report"
}
```

### `GET /health/db`

用途：检查后端是否可以连接 PostgreSQL。

权限：不需要登录。

返回示例：

```json
{
  "status": "ok",
  "database": 1
}
```

## 七、认证与当前用户

### `POST /api/auth/login`

用途：登录并建立登录态。

使用页面：统一登录页。

权限：不需要登录。

请求参数：

```json
{
  "account": "employee",
  "password": "employee123"
}
```

返回数据：当前用户信息、角色、权限范围或访问令牌。

关键业务规则：

- 停用账号不能登录。
- 密码后续必须安全保存，不能明文入库。
- 返回给前端的数据不应包含明文密码。

备注：当前代码存在 `POST /api/login`，后续正式化时建议迁移到本接口。

### `GET /api/me`

用途：获取当前登录用户。

使用页面：所有需要登录态的页面。

权限：已登录用户。

返回数据：当前用户 ID、账号、姓名、角色。

关键业务规则：

- 前端页面刷新后应通过本接口恢复当前用户身份。
- 后端不能相信前端自己存的角色信息。

### `POST /api/auth/logout`

用途：退出登录。

使用页面：所有登录后页面。

权限：已登录用户。

返回数据：退出结果。

## 八、账号管理接口

### `GET /api/admin/accounts`

用途：获取当前管理员可见账号列表。

使用页面：后台账号管理页、后台查询筛选。

权限：

- 超级权限返回全部账号。
- 普通管理员返回自己和自己管理的员工账号。

返回数据：账号 ID、账号名称、姓名、角色、启用状态、管理人、可报工工序。

关键业务规则：

- 普通管理员不能看到权限范围外账号。
- 返回数据不应包含明文密码。

备注：当前接口仍返回 `password` 以兼容现有页面，后续必须移除。

### `POST /api/admin/accounts`

用途：新增账号。

使用页面：后台账号管理页。

权限：

- 超级权限可新增超级权限、管理员、员工账号。
- 普通管理员只能新增员工账号。

关键业务规则：

- 账号名称不可重复。
- 普通管理员新增员工后，该员工默认归属于当前管理员。
- 密码后续必须安全保存。

### `PATCH /api/admin/accounts/{account_id}`

用途：修改账号基础信息。

使用页面：后台账号管理页。

权限：

- 超级权限可修改全局账号。
- 普通管理员只能修改自己权限范围内员工账号的允许字段。

关键业务规则：

- 普通管理员不能把员工改成管理员或超级权限。
- 停用账号不能登录。
- 权限范围必须由后端判断。

### `PATCH /api/admin/accounts/{account_id}/disable`

用途：停用账号。

使用页面：后台账号管理页。

权限：

- 超级权限可停用权限范围内账号。
- 普通管理员只能停用自己管理的员工账号。

关键业务规则：

- 停用后不能登录。
- 历史报工和工资仍然可查询。

### `DELETE /api/admin/accounts/{account_id}`

用途：物理删除账号。

使用页面：后台账号管理页。

权限：仅超级权限。

关键业务规则：

- 普通管理员不能调用成功。
- 不能删除当前登录账号。
- 不能破坏已提交报工记录和历史工资归档。
- 如账号存在历史报工，后端必须保留必要归档信息，或拒绝删除并提示先停用。

## 九、工序管理接口

### `GET /api/admin/processes`

用途：获取工序列表。

使用页面：后台工序管理页、后台查询筛选。

权限：管理员。

返回数据：工序 ID、名称、当前单价、单位、启用状态。

关键业务规则：

- 停用工序仍要在后台列表中可见。
- 员工端不能直接使用本接口获取全量工序。

### `POST /api/admin/processes`

用途：新增工序。

使用页面：后台工序管理页。

权限：管理员。

关键业务规则：

- 工序名称不可重复。
- 单价不能小于 0。
- 新增后默认启用。

### `PATCH /api/admin/processes/{process_id}`

用途：修改工序名称、当前单价、单位或状态。

使用页面：后台工序管理页。

权限：管理员。

关键业务规则：

- 修改当前单价不影响历史报工记录和历史工资。
- 历史工资必须按报工记录保存的当时单价统计。

### `PATCH /api/admin/processes/{process_id}/disable`

用途：停用工序。

使用页面：后台工序管理页。

权限：管理员。

关键业务规则：

- 停用后员工不能继续选择该工序。
- 历史报工仍然可查询。

### `DELETE /api/admin/processes/{process_id}`

用途：物理删除工序。

使用页面：后台工序管理页。

权限：仅超级权限。

关键业务规则：

- 普通管理员不能调用成功。
- 不能破坏已提交报工记录和历史工资归档。
- 如工序存在历史报工，后端必须保留必要归档信息，或拒绝删除并提示先停用。

## 十、员工报工接口

### `GET /api/employee/processes`

用途：获取当前员工可报工的启用工序。

使用页面：员工报工页。

权限：员工。

关键业务规则：

- 后端从登录态识别当前员工。
- 只返回该员工被配置且状态为启用的工序。

备注：当前代码存在 `GET /api/accounts/{account_id}/processes`，后续应迁移到本接口。

### `GET /api/employee/work-reports`

用途：获取当前员工某日期报工记录。

使用页面：员工报工页。

权限：员工。

请求参数：

```text
date=2026-06-04
```

关键业务规则：

- 后端从登录态识别当前员工。
- 返回该日期已提交记录和当日工资。

备注：当前代码存在 `GET /api/work-reports/{account_id}/{work_date}`，后续应迁移到本接口。

### `POST /api/employee/work-reports`

用途：提交当前员工某日期首次报工。

使用页面：员工报工页。

权限：员工。

请求参数：

```json
{
  "workDate": "2026-06-04",
  "rows": [
    {
      "processId": "p-sew",
      "quantity": 12
    }
  ]
}
```

关键业务规则：

- 不能提交未来日期。
- 至少提交一条有效记录。
- 数量必须大于 0。
- 同一天同一个工序只能提交一次。
- 同一员工同一日期已有任意报工记录后，不能再次提交、覆盖、删除或修改。
- 工资由后端按提交时工序当前单价计算并保存。
- 只能提交当前员工被配置且启用的工序。

备注：当前代码存在 `PUT /api/work-reports/{account_id}`，后续应迁移到本接口。

## 十一、员工查询接口

### `GET /api/employee/work-report-history`

用途：查询当前员工历史报工。

使用页面：员工查询页、员工报工页当月汇总。

权限：员工。

请求参数：可选日期范围、月份、工序 ID、分页参数。

关键业务规则：

- 后端从登录态识别当前员工。
- 历史工资按报工记录保存的当时单价统计。
- 工序当前单价变化不能影响历史金额。

备注：当前代码存在 `GET /api/work-report-history/{account_id}`，后续应迁移到本接口。

### `GET /api/employee/monthly-wage-summary`

用途：获取当前员工月度工资汇总。

使用页面：员工报工页、员工查询页。

权限：员工。

请求参数：

```text
month=2026-06
```

关键业务规则：

- 汇总金额必须来自已提交报工记录的小计金额。
- 管理员确认状态不影响工资汇总。

## 十二、管理员查询接口

### `GET /api/admin/work-report-summary`

用途：管理员查询权限范围内员工报工汇总。

使用页面：后台数据查询页。

权限：

- 超级权限可查询全部员工。
- 普通管理员只能查询自己管理的员工。

请求参数：可选员工 ID、开始日期、结束日期、月份、工序 ID、分页参数。

返回数据：员工、日期、工序、数量、工资、统计范围和汇总金额。

关键业务规则：

- 后端必须按登录态校验员工范围。
- 工资总额按报工记录保存的小计金额汇总。
- 不能用工序当前单价重算历史工资。

备注：正式数据量变大后，后台查询页必须使用本接口，不能逐个员工拉取明细后在前端汇总。

### `PATCH /api/admin/work-reports/{report_id}/confirm`

用途：管理员确认员工报工记录。

使用页面：后台数据查询页或确认页。

权限：

- 超级权限可确认全局记录。
- 普通管理员只能确认自己权限范围内员工记录。

关键业务规则：

- 确认状态只影响展示。
- 确认状态不影响工资计算。
- 已确认记录仍不能修改数量、工序、单价或金额。

## 十三、当前过渡接口

当前代码中已有以下演示接口，短期可以保留以兼容前端：

- `POST /api/login`
- `GET /api/admin/accounts`
- `POST /api/admin/accounts`
- `PATCH /api/admin/accounts/{account_id}`
- `DELETE /api/admin/accounts/{account_id}`
- `GET /api/admin/processes`
- `POST /api/admin/processes`
- `PATCH /api/admin/processes/{process_id}`
- `DELETE /api/admin/processes/{process_id}`
- `GET /api/accounts/{account_id}/processes`
- `GET /api/work-reports/{account_id}/{work_date}`
- `GET /api/work-report-history/{account_id}`
- `PUT /api/work-reports/{account_id}`

过渡接口的清理方向：

- 登录迁移到 `/api/auth/login`。
- 当前用户迁移到 `/api/me`。
- 员工端接口移除路径中的 `account_id`。
- 后台查询迁移到聚合查询接口。
- 响应中移除明文密码。
- 后端补齐登录态和权限校验。

## 十四、接口登记模板

新增接口后，必须按下面格式登记。

```text
### `METHOD /api/path`

用途：

使用页面：

是否复用已有能力：

权限：

请求参数：

返回数据：

关键业务规则：

备注：
```
