"""Replay the independent field-set oracle through mixed sync/async contracts."""
import unittest
import test_async_field_return_model as model


class HelperContractModel(model.FieldReturnModel):
    @staticmethod
    def make_program(body,use):
        body=body.replace('yield;','')
        return f'''struct View{{left:Int,data:&mut Int,right:Int}}
          fn pick(v:&mut View)->&mut Int{{{body}}}
          async fn work(v:&mut View)->&mut Int{{yield;return pick(v);}}
          fn get(v:&mut View)->&mut Int{{let h=runtime::spawn(->work(v));
            return match h.join(){{Ok(n)=>{{n}},Err(_)=>{{&mut *v.data}}}};}}
          fn main(){{let mut memory=pool<Int>(1);let mut data=memory.new(7);
            let mut v=View{{left:2,data:&mut data,right:3}};
            let n=get(&mut v);{use}
            print(v.left);print(v.right);print(data);}}'''


if __name__=='__main__':unittest.main()
