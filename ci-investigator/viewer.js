const el = id => document.getElementById(id);
let runs, tool = 'matrix';
function render() {
  const r = runs.find(item => item.run === Number(el('run').value));
  const url = 'https://github.com/'+r.repo+'/actions/runs/'+r.run;
  el('source').href = url+'/attempts/'+r.attempt;
  const failed = r.jobs.filter(j => ['failure','timed_out','startup_failure'].includes(j.result));
  const groups = new Map();
  for (const j of failed) {
    const labels = tool === 'matrix' ? new Set(j.steps) : tool === 'failures' ? [j.job] : j.steps.length ? [] : ['No failed step reported'];
    for (const label of labels) {
      if (!groups.has(label)) groups.set(label,[]);
      groups.get(label).push(j);
    }
  }
  el('summary').textContent = r.jobs.length+' jobs · '+failed.length+' failed · '+failed.filter(j=>!j.steps.length).length+' without step evidence · attempt '+r.attempt;
  const parent = el('results');parent.replaceChildren();
  if (!groups.size) parent.textContent=tool==='unknown'?'All failed jobs have recorded step evidence.':'No matching step evidence in this run.';
  for(const [label,jobs] of [...groups].sort((a,b)=>b[1].length-a[1].length || a[0].localeCompare(b[0]))){
    const detail=document.createElement('details'), heading=document.createElement('summary'), list=document.createElement('ul');
    heading.textContent=label+(tool==='matrix'?' · '+jobs.length+' job'+(jobs.length===1?'':'s'):'');
    for(const j of jobs){
      const li=document.createElement('li'), a=document.createElement('a');a.href=url+'/job/'+j.id;a.textContent=j.job;li.append(a);
      if(tool==='failures'){const note=document.createElement('small');note.textContent=j.steps.join(' · ') || 'No failed step reported';li.append(note)}
      list.append(li);
    }
    detail.append(heading,list);parent.append(detail);
  }
  for(const button of document.querySelectorAll('[data-tool]'))button.setAttribute('aria-pressed',String(button.dataset.tool===tool));
}
async function loadLatest(){
  const button=el('latest'), state=el('liveStatus');
  button.disabled=true;
  const repo=runs.find(r=>r.run===Number(el('run').value)).repo;
  async function github(path){
    const res=await fetch('https://api.github.com/repos/'+repo+'/actions/runs'+path,{signal:AbortSignal.timeout(15000)});
    if(!res.ok)throw Error('GitHub returned HTTP '+res.status);
    return res.json();
  }
  try{
    state.textContent='Checking '+repo+'…';
    const meta=(await github('?status=failure&per_page=1')).workflow_runs[0];
    if(!meta)throw Error('No failed run found');
    const jobs=[];
    for(let page=1;page<=10;page++){
      const batch=await github('/'+meta.id+'/attempts/'+meta.run_attempt+'/jobs?per_page=100&page='+page);
      for(const j of batch.jobs)jobs.push({job:j.name,id:j.id,result:j.conclusion,steps:(j.steps||[]).filter(s=>s.conclusion==='failure').map(s=>s.name)});
      if(jobs.length>=batch.total_count)break;
      if(page===10)throw Error('Run exceeds the 1,000-job limit');
    }
    const run={repo,run:meta.id,attempt:meta.run_attempt,workflow:meta.name,jobs};
    runs=runs.filter(r=>r.run!==run.run);runs.push(run);
    if(![...el('run').options].some(o=>o.value===String(run.run)))el('run').add(new Option(repo+' · '+meta.name+' · '+run.run,run.run));
    el('run').value=String(run.run);render();state.textContent='Loaded directly from GitHub.';
  }catch(error){state.textContent='Live refresh unavailable. '+error.message+'. The selected run is still available.'}
  finally{button.disabled=false}
}
try{
  const response=await fetch('runs.json');if(!response.ok) throw Error();
  runs=await response.json();
  for(const r of runs)el('run').add(new Option(r.repo+' · '+r.workflow+' · '+r.run,r.run));
  el('run').value='45849948162';el('run').onchange=render;el('latest').onclick=loadLatest;
  for(const b of document.querySelectorAll('[data-tool]'))b.onclick=()=>{tool=b.dataset.tool;render()};
  render();
}catch{el('summary').textContent='Captured jobs could not be loaded. Reload the page or serve this folder over HTTP.'}
