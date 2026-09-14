(()=>{
"use strict";

if(window.__PHOENIX_START_V441_RUNTIME_GUARD__)return;

const state=window.__PHOENIX_START_V441_RUNTIME_GUARD__={
  version:"1.0.1",
  mode:"BOUNDED_ONE_SHOT",
  runs:0,
  replacements:0,
  timers:[]
};

const STALE=/START\s+v(?:3\.0\.2|3\.0)(?![\d.])/g;

function normalizeText(value){
  if(!value||!value.includes("START"))return value;
  return value.replace(STALE,"START v4.41");
}

function repairVisibleRuntimeLabel(){
  state.runs++;
  if(!document.body)return 0;

  let count=0;
  const walker=document.createTreeWalker(
    document.body,
    NodeFilter.SHOW_TEXT,
    {
      acceptNode(node){
        const parent=node.parentElement;
        if(!parent)return NodeFilter.FILTER_REJECT;
        const tag=(parent.tagName||"").toLowerCase();
        if(tag==="script"||tag==="style"||tag==="noscript"||tag==="template"){
          return NodeFilter.FILTER_REJECT;
        }
        return node.nodeValue&&node.nodeValue.includes("START")
          ?NodeFilter.FILTER_ACCEPT
          :NodeFilter.FILTER_REJECT;
      }
    }
  );

  let node;
  while((node=walker.nextNode())){
    const before=node.nodeValue;
    const after=normalizeText(before);
    if(after!==before){
      node.nodeValue=after;
      count++;
    }
  }

  state.replacements+=count;
  return count;
}

function run(){
  try{repairVisibleRuntimeLabel();}catch(_err){}
}

function armBoundedRuns(){
  for(const delay of [0,100,350,900,1800,3500,6000]){
    state.timers.push(window.setTimeout(run,delay));
  }
}

if(document.readyState==="loading"){
  document.addEventListener("DOMContentLoaded",armBoundedRuns,{once:true});
}else{
  armBoundedRuns();
}
window.addEventListener("pageshow",run,{passive:true});
})();
