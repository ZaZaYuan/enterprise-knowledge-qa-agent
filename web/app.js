const $ = (id) => document.getElementById(id);
const statusNames = {answered:'已核实回答', conflict:'资料冲突 · 待确认', insufficient:'资料不足', tool_error:'工具暂不可用', model_error:'模型暂不可用', incomplete:'未完成'};
const actionNames = {search_docs:'检索资料', read_doc:'读取原文', check_conflicts:'核对冲突', submit_answer:'提交答案', protocol_error:'协议校验'};
let history = [];
let lastResult = null;

async function health(){
  try{const res=await fetch('/api/health');const data=await res.json();$('provider').textContent=`${data.provider==='deepseek'?'DEEPSEEK · LIVE':'OFFLINE · MOCK'} · ${data.document_count} 份资料`;}
  catch{$('provider').textContent='连接不可用';}
}

function node(tag, cls, text){const el=document.createElement(tag);if(cls)el.className=cls;if(text!==undefined)el.textContent=text;return el;}
function showNotice(text, error=false){const el=$('notice');el.textContent=text;el.className='notice'+(error?' error':'');el.hidden=false;}
function clearNotice(){$('notice').hidden=true;}

function render(result){
  lastResult=result;
  $('result').hidden=false;
  $('result-badge').className='badge '+result.status;
  $('result-badge').textContent=statusNames[result.status]||result.status;
  $('meta').textContent=`${result.model} · ${result.steps} 轮决策 · ${result.tool_calls} 次工具调用`;
  $('result-question').textContent=result.question;
  $('answer').textContent=result.answer;
  const missing=$('missing');missing.hidden=!result.missing_info.length;
  missing.textContent=result.missing_info.length?'待补充：'+result.missing_info.join('；'):'';
  const evidence=$('citations');evidence.replaceChildren();
  if(!result.citations.length)evidence.append(node('p','empty-cite','当前无可引用原文，Agent 已说明原因。'));
  for(const citation of result.citations){const card=node('div','citation');card.append(node('strong','',citation.doc_id));card.append(node('p','',`“${citation.quote}”`));evidence.append(card);}
  const trace=$('trace');trace.replaceChildren();
  result.trace.forEach((event,index)=>{const rejected=Boolean(event.result?.error);const card=node('div','trace-step'+(rejected?' rejected':''));card.append(node('span','step-num',`STEP ${String(index+1).padStart(2,'0')}`));card.append(node('strong','',actionNames[event.action]||event.action));card.append(node('p','',event.summary||''));trace.append(card);});
  $('result').scrollIntoView({behavior:'smooth',block:'start'});
}

async function ask(question){
  const submit=$('submit');submit.disabled=true;submit.textContent='正在核查…';showNotice('Agent 正在检索资料并核对原文，请稍候。');
  try{
    const response=await fetch('/api/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question,history})});
    const data=await response.json();
    if(!response.ok)throw new Error(data.error||'请求失败');
    render(data);clearNotice();
    history.push({role:'user',content:question},{role:'assistant',content:data.answer});
    history=history.slice(-8);
  }catch(error){showNotice(error.message||'服务不可用',true);}
  finally{submit.disabled=false;submit.innerHTML='开始核查 <span>→</span>';}
}

$('ask-form').addEventListener('submit',(event)=>{event.preventDefault();const question=$('question').value.trim();if(question)ask(question);});
document.querySelectorAll('[data-question]').forEach(button=>button.addEventListener('click',()=>{
  const question=button.dataset.question;
  if(question==='那紧急情况呢？'&&!history.some(item=>item.role==='user'&&item.content.includes('事假'))){
    history=[{role:'user',content:'普通事假要提前几天申请？'},{role:'assistant',content:'普通事假至少提前 2 个工作日向直属主管提交申请。依据 L01。'}];
  }
  $('question').value=question;ask(question);
}));
$('download').addEventListener('click',()=>{
  if(!lastResult)return;
  const blob=new Blob([JSON.stringify(lastResult,null,2)],{type:'application/json'});
  const url=URL.createObjectURL(blob);const link=document.createElement('a');link.href=url;link.download=`knowledge-agent-${lastResult.status}.json`;link.click();URL.revokeObjectURL(url);
});
health();
