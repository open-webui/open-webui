import{_ as e,l as s,I as o,d as i,K as g}from"./BTaIz8BB.js";import{p as d}from"./Dv4iM9dU.js";var p={parse:e(async r=>{const a=await d("info",r);s.debug(a)},"parse")},v={version:g.version+""},c=e(()=>v.version,"getVersion"),m={getVersion:c},l=e((r,a,n)=>{s.debug(`rendering info diagram
`+r);const t=o(a);i(t,100,400,!0),t.append("g").append("text").attr("x",100).attr("y",40).attr("class","version").attr("font-size",32).style("text-anchor","middle").text(`v${n}`)},"draw"),f={draw:l},b={parser:p,db:m,renderer:f};export{b as diagram};
//# sourceMappingURL=BjT5hISN.js.map
