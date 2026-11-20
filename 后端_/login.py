from fastapi import FastAPI,HTTPException
from pydantic import BaseModel

app=FastAPI(title='登录界面')

TEST_USER={
    'username':'test',
    'password':'123456'
}

class LoginRequest(BaseModel):
    username:str
    password:str

@app.get('/hello')
def hello():
    return 'hello world'

@app.post('/login')
def login(data:LoginRequest):
    if data.username==TEST_USER['username'] and data.password==TEST_USER['password']:
        return {'code':200,'message':'登陆成功','username':data.username}
    raise HTTPException(status_code=401,detail='用户名或密码错误')

if __name__=="__main__":
    import uvicorn
    uvicorn.run("login:app",host="127.0.0.1", port=8000, reload=True)