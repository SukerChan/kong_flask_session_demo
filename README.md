# kong_flask_session_demo
本demo主要目的为融合kong与flask，希望借助kong完成用户方面的登录、访问控制等
## 原理
借助kong的session auth，对于用户的登录请求鉴定后，向kong系统做一次登录操作，将得到的cookie set到flask的client，这样之后的client请求也可以直接通过kong的authentication
## 步骤
- 配置kong，为服务创建相应的service、route等，本例中route配置为/kong_flask_demo
- 参考sample.env创建.env，主要需要修改KONG_HOST和KONG_FLASK_LOGIN_URL，配置为kong和服务相应的地址
- 为service配置auth plugin。session auth需要与另一个auth配合使用，本例只为demo，所以使用了key auth  
session auth配置中的cookie name与.env中的KONG_COOKIE_NAME相同
- 创建consumer与key。本例中需要为consumer添加**APP_NAME**的tag，costom_id也为 **APP_NAME+"_"+id** 的格式，id为服务的用户id。  
如本例中，APP_NAME在.env中配置为**kong_flask_demo**，则服务中id为1的用户suker在kong consumers中的配置应该至少如下：
```json
    {
      "id": "e56dcf08-d699-45df-8462-f532836d818f",
      "created_at": 1612856215, 
      "username": "suker", 
      "custom_id": "kong_flask_demo_1",
      "tags": ["kong_flask_demo"]
    }
```
另外，需要添加一个anonymous用户，并配置在使用的auth plugin上  
参考：  
https://docs.konghq.com/hub/kong-inc/session/  
https://docs.konghq.com/hub/kong-inc/key-auth/  
## api
demo的api设计比较简单，只有三个：  
- /
- /login/<username>
- /logout  

其中，/ 可以显示当前的登录状态；  
login接口可以尝试登录username的用户，如果username不存在或当前已经是登录状态，则会失败；  
logout接口可以退出登录
## 测试方式
api的返回中都加入了request的headers，这样可以便于测试者观察request通过kong之后，kong对request做的调整。
- 初始状态下，直接访问 / 接口，会提示当前是anonymous状态，查看request headers也可以看到X-Anonymous-Consumer为true
- 调用login进行登录，可以尝试使用已经在kong consumer中按条件添加的用户名与未按条件添加的用户名，或不存在的consumer用户名等  
- 调用login成功后，再访问 / 接口，可以看到当前已经是登录状态
## 可以使用场景讨论
- 根据当前对kong中auth plugin的调研，kong可以帮助服务维护系统登录的状态。另外，可以借助route的配置实现权限管理，借助rate limit实现流量管理
- 但kong只能帮助维护粗粒度的权限管理。但是当访问次数涉及到同一请求可允许用户同周期访问多次(只计1次)的这样的应用场景(如用户购买了一个月使用多少次类的套餐)，我暂时没有找到相应的plugin可以满足
- kong也有JWT auth plugin，enguang可以调研一下如何或者是否可以融入我们的用户系统中
