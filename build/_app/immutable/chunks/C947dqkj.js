import"./CWj6FrbW.js";import"./69_IOA4Y.js";import{p as U,o as V,d as W,e as X,a as v,b as Y,i as Z,m as $,j as ee,f as b,t as M,w as n,u as y,r as te}from"./0WpKKl27.js";import{i as ae}from"./Cmf4RC8y.js";import{e as ne,i as oe}from"./u5Cnd4mY.js";import{f as ie,s as le}from"./CZ1y6KaE.js";import{i as re}from"./C3k0oZ3o.js";import{p as t}from"./DpN1w328.js";const _e=r=>{typeof document>"u"||document.documentElement.style.setProperty("--app-text-scale",`${r}`)};var se=b('<div class="confetti svelte-rtt661"></div>'),de=b("<div></div>");function Ce(r,e){U(e,!1);let z=t(e,"size",8,10),s=t(e,"x",24,()=>[-.5,.5]),d=t(e,"y",24,()=>[.25,1]),c=t(e,"duration",8,2e3),f=t(e,"infinite",8,!1),l=t(e,"delay",24,()=>[0,50]),g=t(e,"colorRange",24,()=>[0,360]),m=t(e,"colorArray",24,()=>[]),R=t(e,"amount",8,50),u=t(e,"iterationCount",8,1),k=t(e,"fallDistance",8,"100px"),w=t(e,"rounded",8,!1),S=t(e,"cone",8,!1),A=t(e,"noGravity",8,!1),D=t(e,"xSpread",8,.15),F=t(e,"destroyOnComplete",8,!0),G=t(e,"disableForReducedMotion",8,!1),h=$(!1);V(()=>{!F()||f()||u()=="infinite"||setTimeout(()=>Z(h,!0),(c()+l()[1])*u())});function a(o,i){return Math.random()*(i-o)+o}function O(){return m().length?m()[Math.round(Math.random()*(m().length-1))]:`hsl(${Math.round(a(g()[0],g()[1]))}, 75%, 50%)`}re();var x=W(),T=X(x);{var j=o=>{var i=de();let _;ne(i,5,()=>({length:R()}),oe,(B,ce)=>{var C=se();M((E,P,p,q,H,I,J,K,L,N,Q)=>ie(C,`
        --fall-distance: ${k()??""};
        --size: ${z()??""}px;
        --color: ${E??""};
        --skew: ${P??""}deg,${p??""}deg;
        --rotation-xyz: ${q??""}, ${H??""}, ${I??""};
        --rotation-deg: ${J??""}deg;
        --translate-y-multiplier: ${K??""};
        --translate-x-multiplier: ${L??""};
        --scale: ${N??""};
        --transition-duration: ${f()?`calc(${c()}ms * var(--scale))`:`${c()}ms`};
        --transition-delay: ${Q??""}ms;
        --transition-iteration-count: ${(f()?"infinite":u())??""};
        --x-spread: ${1-D()}`),[()=>n(O),()=>n(()=>a(-45,45)),()=>n(()=>a(-45,45)),()=>n(()=>a(-10,10)),()=>n(()=>a(-10,10)),()=>n(()=>a(-10,10)),()=>n(()=>a(0,360)),()=>(y(d()),n(()=>a(d()[0],d()[1]))),()=>(y(s()),n(()=>a(s()[0],s()[1]))),()=>n(()=>.1*a(2,10)),()=>(y(l()),n(()=>a(l()[0],l()[1])))]),v(B,C)}),te(i),M(()=>_=le(i,1,"confetti-holder svelte-rtt661",null,_,{rounded:w(),cone:S(),"no-gravity":A(),"reduced-motion":G()})),v(o,i)};ae(T,o=>{ee(h)||o(j)})}v(r,x),Y()}export{Ce as C,_e as s};
//# sourceMappingURL=C947dqkj.js.map
