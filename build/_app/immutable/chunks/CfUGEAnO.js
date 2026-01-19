import"./CWj6FrbW.js";import"./69_IOA4Y.js";import{p as Se,g as Ve,q as ne,u as P,v as je,f as _,e as He,c as a,r,l as de,a as m,j as n,n as b,k as d,t as h,w as o,m as M,i as g,s as c,b as Oe,x as U}from"./0WpKKl27.js";import{i as Ue}from"./Cmf4RC8y.js";import{r as W,a as z}from"./CZ1y6KaE.js";import{b as L}from"./kb1CvZ3a.js";import{b as ue}from"./Bo3ZTtFv.js";import{p as We}from"./Bfc47y5P.js";import{i as ze}from"./C3k0oZ3o.js";import{p}from"./DpN1w328.js";import{a as Le,s as Ge}from"./BVrWTcfB.js";import{g as Je}from"./B5RARo22.js";import{C as Ke}from"./hEP_3Uio.js";import{C as Qe}from"./ByHAJgVC.js";import{B as Re}from"./DUufguWK.js";import{T as q}from"./Db0gdTVr.js";import{C as Xe}from"./B0N4-HfZ.js";var Ye=_('<button class="w-full text-left text-sm py-1.5 px-1 rounded-lg dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-gray-850" type="button"><!></button>'),Ze=_('<input class="w-full text-2xl font-medium bg-transparent outline-hidden font-primary" type="text" required/>'),et=_('<div class="text-sm text-gray-500 shrink-0"> </div>'),tt=_('<input class="w-full text-sm disabled:text-gray-500 bg-transparent outline-hidden" type="text" required/>'),at=_('<input class="w-full text-sm bg-transparent outline-hidden" type="text" required/>'),rt=_('<div class="text-sm text-gray-500"><div class=" bg-yellow-500/20 text-yellow-700 dark:text-yellow-200 rounded-lg px-4 py-3"><div> </div> <ul class=" mt-1 list-disc pl-4 text-xs"><li> </li> <li> </li></ul></div> <div class="my-3"> </div></div>'),it=_('<div class=" flex flex-col justify-between w-full overflow-y-auto h-full"><div class="mx-auto w-full md:px-0 h-full"><form class=" flex flex-col max-h-[100dvh] h-full"><div class="flex flex-col flex-1 overflow-auto h-0 rounded-lg"><div class="w-full mb-2 flex flex-col gap-0.5"><div class="flex w-full items-center"><div class=" shrink-0 mr-2"><!></div> <div class="flex-1"><!></div> <div><!></div></div> <div class=" flex gap-2 px-1 items-center"><!> <!></div></div> <div class="mb-2 flex-1 overflow-auto h-0 rounded-lg"><!></div> <div class="pb-3 flex justify-between"><div class="flex-1 pr-3"><div class="text-xs text-gray-500 line-clamp-2"><span class=" font-semibold dark:text-gray-200"> </span> <br/>— <span class=" font-medium dark:text-gray-400"> </span></div></div> <button class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full" type="submit"> </button></div></div></form></div></div> <!>',1);function wt(ce,f){Se(f,!1);const e=()=>Le(me,"$i18n",fe),[fe,ve]=Ge(),me=Ve("i18n");let w=M(null),A=M(!1),pe=p(f,"onSave",8,()=>{}),x=p(f,"edit",8,!1),G=p(f,"clone",8,!1),k=p(f,"id",12,""),y=p(f,"name",12,""),$=p(f,"meta",28,()=>({description:""})),v=p(f,"content",12,""),F=M("");const _e=()=>{g(F,v())};let I=M(),he=`"""
title: Example Filter
author: open-webui
author_url: https://github.com/open-webui
funding_url: https://github.com/open-webui
version: 0.1
"""

from pydantic import BaseModel, Field
from typing import Optional


class Filter:
    class Valves(BaseModel):
        priority: int = Field(
            default=0, description="Priority level for the filter operations."
        )
        max_turns: int = Field(
            default=8, description="Maximum allowable conversation turns for a user."
        )
        pass

    class UserValves(BaseModel):
        max_turns: int = Field(
            default=4, description="Maximum allowable conversation turns for a user."
        )
        pass

    def __init__(self):
        # Indicates custom file handling logic. This flag helps disengage default routines in favor of custom
        # implementations, informing the WebUI to defer file-related operations to designated methods within this class.
        # Alternatively, you can remove the files directly from the body in from the inlet hook
        # self.file_handler = True

        # Initialize 'valves' with specific configurations. Using 'Valves' instance helps encapsulate settings,
        # which ensures settings are managed cohesively and not confused with operational flags like 'file_handler'.
        self.valves = self.Valves()
        pass

    def inlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        # Modify the request body or validate it before processing by the chat completion API.
        # This function is the pre-processor for the API where various checks on the input can be performed.
        # It can also modify the request before sending it to the API.
        print(f"inlet:{__name__}")
        print(f"inlet:body:{body}")
        print(f"inlet:user:{__user__}")

        if __user__.get("role", "admin") in ["user", "admin"]:
            messages = body.get("messages", [])

            max_turns = min(__user__["valves"].max_turns, self.valves.max_turns)
            if len(messages) > max_turns:
                raise Exception(
                    f"Conversation turn limit exceeded. Max turns: {max_turns}"
                )

        return body

    def outlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        # Modify or analyze the response body after processing by the API.
        # This function is the post-processor for the API, which can be used to modify the response
        # or perform additional checks and analytics.
        print(f"outlet:{__name__}")
        print(f"outlet:body:{body}")
        print(f"outlet:user:{__user__}")

        return body
`;const ge=async()=>{pe()({id:k(),name:y(),meta:$(),content:v()})},J=async()=>{if(n(I)){v(n(F)),await U();const t=await n(I).formatPythonCodeHandler();await U(),v(n(F)),await U(),t&&(console.info("Code formatted successfully"),ge())}};ne(()=>P(v()),()=>{v()&&_e()}),ne(()=>(P(y()),P(x()),P(G())),()=>{y()&&!x()&&!G()&&k(y().replace(/\s+/g,"_").toLowerCase())}),je(),ze();var K=it(),B=He(K),Q=a(B),C=a(Q),R=a(C),E=a(R),T=a(E),D=a(T),xe=a(D);{let t=b(()=>(e(),o(()=>e().t("Back"))));q(xe,{get content(){return n(t)},children:(l,u)=>{var i=Ye(),s=a(i);Xe(s,{strokeWidth:"2.5"}),r(i),de("click",i,()=>{Je("/admin/functions")}),m(l,i)},$$slots:{default:!0}})}r(D);var N=d(D,2),ye=a(N);{let t=b(()=>(e(),o(()=>e().t("e.g. My Filter"))));q(ye,{get content(){return n(t)},placement:"top-start",children:(l,u)=>{var i=Ze();W(i),h(s=>z(i,"placeholder",s),[()=>(e(),o(()=>e().t("Function Name")))]),L(i,y),m(l,i)},$$slots:{default:!0}})}r(N);var X=d(N,2),be=a(X);{let t=b(()=>(e(),o(()=>e().t("Function"))));Re(be,{type:"muted",get content(){return n(t)}})}r(X),r(T);var Y=d(T,2),Z=a(Y);{var we=t=>{var l=et(),u=a(l,!0);r(l),h(()=>c(u,k())),m(t,l)},ke=t=>{{let l=b(()=>(e(),o(()=>e().t("e.g. my_filter"))));q(t,{className:"w-full",get content(){return n(l)},placement:"top-start",children:(u,i)=>{var s=tt();W(s),h(H=>{z(s,"placeholder",H),s.disabled=x()},[()=>(e(),o(()=>e().t("Function ID")))]),L(s,k),m(u,s)},$$slots:{default:!0}})}};Ue(Z,t=>{x()?t(we):t(ke,!1)})}var $e=d(Z,2);{let t=b(()=>(e(),o(()=>e().t("e.g. A filter to remove profanity from text"))));q($e,{className:"w-full self-center items-center flex",get content(){return n(t)},placement:"top-start",children:(l,u)=>{var i=at();W(i),h(s=>z(i,"placeholder",s),[()=>(e(),o(()=>e().t("Function Description")))]),L(i,()=>$().description,s=>$($().description=s,!0)),m(l,i)},$$slots:{default:!0}})}r(Y),r(E);var S=d(E,2),Fe=a(S);ue(Ke(Fe,{get value(){return v()},lang:"python",boilerplate:he,onChange:t=>{g(F,t)},onSave:async()=>{n(w)&&n(w).requestSubmit()},$$legacy:!0}),t=>g(I,t),()=>n(I)),r(S);var ee=d(S,2),V=a(ee),te=a(V),j=a(te),Ie=a(j,!0);r(j);var ae=d(j),re=d(ae,3),Ce=a(re,!0);r(re),r(te),r(V);var ie=d(V,2),Pe=a(ie,!0);r(ie),r(ee),r(R),r(C),ue(C,t=>g(w,t),()=>n(w)),r(Q),r(B);var Me=d(B,2);Qe(Me,{get show(){return n(A)},set show(t){g(A,t)},$$events:{confirm:()=>{J()}},children:(t,l)=>{var u=rt(),i=a(u),s=a(i),H=a(s,!0);r(s);var se=d(s,2),O=a(se),qe=a(O,!0);r(O);var oe=d(O,2),Ae=a(oe,!0);r(oe),r(se),r(i);var le=d(i,2),Be=a(le,!0);r(le),r(u),h((Ee,Te,De,Ne)=>{c(H,Ee),c(qe,Te),c(Ae,De),c(Be,Ne)},[()=>(e(),o(()=>e().t("Please carefully review the following warnings:"))),()=>(e(),o(()=>e().t("Functions allow arbitrary code execution."))),()=>(e(),o(()=>e().t("Do not install functions from sources you do not fully trust."))),()=>(e(),o(()=>e().t("I acknowledge that I have read and I understand the implications of my action. I am aware of the risks associated with executing arbitrary code and I have verified the trustworthiness of the source.")))]),m(t,u)},$$slots:{default:!0},$$legacy:!0}),h((t,l,u,i)=>{c(Ie,t),c(ae,` ${l??""} `),c(Ce,u),c(Pe,i)},[()=>(e(),o(()=>e().t("Warning:"))),()=>(e(),o(()=>e().t("Functions allow arbitrary code execution."))),()=>(e(),o(()=>e().t("don't install random functions from sources you don't trust."))),()=>(e(),o(()=>e().t("Save")))]),de("submit",C,We(()=>{x()?J():g(A,!0)})),m(ce,K),Oe(),ve()}export{wt as F};
//# sourceMappingURL=CfUGEAnO.js.map
