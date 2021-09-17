import re
import aiomysql
import json

from sanic.models.handler_types import RequestMiddlewareType
class UseMysql:
    def __init__(self):
        self.conn = None
        self.pool = None
        with open('./config/local/usemysql.json') as f:
            self.config = json.load(f)

    async def initpool(self):
        __pool = await aiomysql.create_pool( #双下划线表示这是一个完全的私有变量，单下划线形式上表示私有，但是仍然可以被访问到
            host = self.config['host'],
            port = self.config['port'],
            user = self.config['user'],
            password = self.config['pass'],
            db = self.config['db'],
            autocommit = False,
            minsize = 1,
            maxsize= 5, 
        )
        return __pool
    async def getcursor(self):
        conn = await self.pool.acquire()
        cur = await conn.cursor()
        return conn,cur

    async def returncursor(self,conn,cur):
        if cur:
            await cur.close()
        await self.pool.release(conn)

    async def query(self,query,param=None):
        conn,cur = await self.getcursor()
        try:
            await cur.execute(query,param)
            return await cur.fetchall()
        except Exception as e:
            print(e)
        finally:    #finally会无条件执行，尽管return存在，但是else不会在return后面执行
            await self.returncursor(conn,cur)

    async def commit(self,query,param=None):
        conn,cur = await self.getcursor()
        try:
            await cur.execute(query,param)
            affected_row = cur.rowcount
            await conn.commit()
            if affected_row != 0:
                return affected_row
            else:
                return False
        except Exception as e:
            print(e)
            await conn.rollback()
            return False
        finally:    #finally会无条件执行，尽管return存在，但是else不会在return后面执行
            await self.returncursor(conn,cur)

    async def query_auth(self,account):
        result = await self.query(f"""select hash,salt from user where account='{account}'""")
        if len(result) == 1:
            pass_hash,pass_salt = result[0]
            return pass_hash,pass_salt
        else:
            return False,False

    async def sign_up(self,account,pass_hash,pass_salt):
        result = await self.commit(f"""INSERT INTO user (account,hash,salt)
                 VALUES ('{account}','{pass_hash}','{pass_salt}')""")
        return result

    async def storetoken(self,account,token):
        result = await self.commit(f"""INSERT INTO token (token,account)
                                    VALUES ('{token}','{account}')""")
        print(result)
        return result

    async def minecraft_checkbind(self,account):
        result = await self.query(f"""SELECT `is_bind` FROM `minecraft_account` WHERE `account` = '{account}'""")
        if len(result) == 1:
            if result[0][0] == 1:
                return 1
            else:
                return 0
        else:
            return 2

    async def minecraft_init_account(self,account):
        result = await self.commit(f"""INSERT INTO `minecraft_account` (account,is_bind)
                                    VALUES ('{account}',0)""")
        print(f"=====>创建新minceaft账号记录'{account}'\n=====>影响了{result}行。")

    async def minecraft_store_bind_code(self,account,minecraft_account,new_code,expire_time): 
        result = await self.commit(f"""UPDATE `minecraft_account` SET
                                        `code` = '{new_code}',
                                        `expire` = '{expire_time}',
                                        `minecraft_account` = '{minecraft_account}'
                                        WHERE `account` = '{account}'""")
        print(f"""=====>登记账号{account}的绑定请求，\nminectaft账号为{minecraft_account},\n验证码为{new_code}，\n过期时间为{expire_time}\n=====>影响了{result}行""")

    async def minecraft_getcode(self,account,code):
        result = await self.query(f"""SELECT `code`,`expire` FROM `minecraft_account` WHERE `account` = '{account}'""")
        if len(result) == 1:
            true_code,expire_time = result[0]
            return True,true_code,expire_time
        else:
            return False,None,None

    async def minecraft_store_uuid(self,account,uuid,now_time):
        result = await self.commit(f"""UPDATE `minecraft_account` SET
                                        `minecraft_uuid` = '{uuid}',
                                        `is_bind` = 1,
                                        `bind_time` = '{now_time}',
                                        `expire` = '{now_time}'
                                        WHERE `account` = '{account}'""")
        print(f"""=====>绑定{account}的mincraft_uuid为{uuid}""")

    async def check_account_availability(self,account):
        result = await self.query(f"""SELECT 1 FROM `user` WHERE `account` = '{account}'""")
        return not result
