# Frontend

前端目录，用于 H5 页面。

当前已实现：

1. 统一登录页面
2. 登录后按账号角色分流
3. 后台账号管理页面
4. 后台工序管理页面
5. 后台数据查询入口占位
6. 员工报工页面占位
7. 基于 hash 的前端路由

临时演示账号：

- 超级权限：admin / admin123，登录后进入 `#/admin/accounts`
- 管理员：manager / manager123，登录后进入 `#/admin/accounts`
- 员工：employee / employee123，登录后进入 `#/employee`

后续接入后端认证 API 后，由后端返回当前账号角色，前端按角色跳转。

当前后台账号使用浏览器本地演示数据。工序管理已优先读写后端 `/api/admin/processes` 演示接口；当后端未启动时，会退回到浏览器本地演示数据。
