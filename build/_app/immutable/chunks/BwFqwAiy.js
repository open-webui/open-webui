import"./CWj6FrbW.js";import"./69_IOA4Y.js";import{p as Be,g as Oe,q as he,u as I,v as Ke,f as g,e as ze,i as v,m as $,j as d,n as y,k as u,c as r,r as a,l as O,a as h,t as b,w as l,s as c,b as Je,x as K}from"./0WpKKl27.js";import{i as Qe}from"./Cmf4RC8y.js";import{r as z,a as J}from"./CZ1y6KaE.js";import{b as Q}from"./kb1CvZ3a.js";import{b as ge}from"./Bo3ZTtFv.js";import{p as Ve}from"./Bfc47y5P.js";import{i as Xe}from"./C3k0oZ3o.js";import{p as _}from"./DpN1w328.js";import{a as xe,s as Ze}from"./BVrWTcfB.js";import{g as et}from"./B5RARo22.js";import{u as tt}from"./PCOILo-8.js";import{C as rt}from"./hEP_3Uio.js";import{C as at}from"./ByHAJgVC.js";import{C as st}from"./B0N4-HfZ.js";import{T as D}from"./Db0gdTVr.js";import{L as ot}from"./C1SugFh_.js";import{A as it}from"./BHCb5XAX.js";var lt=g('<button class="w-full text-left text-sm py-1.5 px-1 rounded-lg dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-gray-850" type="button"><!></button>'),nt=g('<input class="w-full text-2xl font-medium bg-transparent outline-hidden font-primary" type="text" required/>'),dt=g('<div class="text-sm text-gray-500 shrink-0"> </div>'),ut=g('<input class="w-full text-sm disabled:text-gray-500 bg-transparent outline-hidden" type="text" required/>'),ct=g('<input class="w-full text-sm bg-transparent outline-hidden" type="text" required/>'),mt=g('<div class="text-sm text-gray-500"><div class=" bg-yellow-500/20 text-yellow-700 dark:text-yellow-200 rounded-lg px-4 py-3"><div> </div> <ul class=" mt-1 list-disc pl-4 text-xs"><li> </li> <li> </li></ul></div> <div class="my-3"> </div></div>'),ft=g('<!> <div class=" flex flex-col justify-between w-full overflow-y-auto h-full"><div class="mx-auto w-full md:px-0 h-full"><form class=" flex flex-col max-h-[100dvh] h-full"><div class="flex flex-col flex-1 overflow-auto h-0 rounded-lg"><div class="w-full mb-2 flex flex-col gap-0.5"><div class="flex w-full items-center"><div class=" shrink-0 mr-2"><!></div> <div class="flex-1"><!></div> <div class="self-center shrink-0"><button class="bg-gray-50 hover:bg-gray-100 text-black dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-white transition px-2 py-1 rounded-full flex gap-1 items-center" type="button"><!> <div class="text-sm font-medium shrink-0"> </div></button></div></div> <div class=" flex gap-2 px-1 items-center"><!> <!></div></div> <div class="mb-2 flex-1 overflow-auto h-0 rounded-lg"><!></div> <div class="pb-3 flex justify-between"><div class="flex-1 pr-3"><div class="text-xs text-gray-500 line-clamp-2"><span class=" font-semibold dark:text-gray-200"> </span> <br/>— <span class=" font-medium dark:text-gray-400"> </span></div></div> <button class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full" type="submit"> </button></div></div></form></div></div> <!>',1);function Nt(ye,m){Be(m,!1);const x=()=>xe(tt,"$user",V),e=()=>xe(we,"$i18n",V),[V,be]=Ze(),we=Oe("i18n");let C=$(null),N=$(!1),M=$(!1),w=_(m,"edit",8,!1),X=_(m,"clone",8,!1),ke=_(m,"onSave",8,()=>{}),E=_(m,"id",12,""),k=_(m,"name",12,""),T=_(m,"meta",28,()=>({description:""})),p=_(m,"content",12,""),j=_(m,"accessControl",28,()=>({})),q=$("");const $e=()=>{v(q,p())};let P=$(),Ce=`import os
import requests
from datetime import datetime
from pydantic import BaseModel, Field

class Tools:
    def __init__(self):
        pass

    # Add your custom tools using pure Python code here, make sure to add type hints and descriptions
	
    def get_user_name_and_email_and_id(self, __user__: dict = {}) -> str:
        """
        Get the user name, Email and ID from the user object.
        """

        # Do not include a descrption for __user__ as it should not be shown in the tool's specification
        # The session user object will be passed as a parameter when the function is called

        print(__user__)
        result = ""

        if "name" in __user__:
            result += f"User: {__user__['name']}"
        if "id" in __user__:
            result += f" (ID: {__user__['id']})"
        if "email" in __user__:
            result += f" (Email: {__user__['email']})"

        if result == "":
            result = "User: Unknown"

        return result

    def get_current_time(self) -> str:
        """
        Get the current time in a more human-readable format.
        """

        now = datetime.now()
        current_time = now.strftime("%I:%M:%S %p")  # Using 12-hour format with AM/PM
        current_date = now.strftime(
            "%A, %B %d, %Y"
        )  # Full weekday, month name, day, and year

        return f"Current Date and Time = {current_date}, {current_time}"

    def calculator(
        self,
        equation: str = Field(
            ..., description="The mathematical equation to calculate."
        ),
    ) -> str:
        """
        Calculate the result of an equation.
        """

        # Avoid using eval in production code
        # https://nedbatchelder.com/blog/201206/eval_really_is_dangerous.html
        try:
            result = eval(equation)
            return f"{equation} = {result}"
        except Exception as e:
            print(e)
            return "Invalid equation"

    def get_current_weather(
        self,
        city: str = Field(
            "New York, NY", description="Get the current weather for a given city."
        ),
    ) -> str:
        """
        Get the current weather for a given city.
        """

        api_key = os.getenv("OPENWEATHER_API_KEY")
        if not api_key:
            return (
                "API key is not set in the environment variable 'OPENWEATHER_API_KEY'."
            )

        base_url = "http://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": city,
            "appid": api_key,
            "units": "metric",  # Optional: Use 'imperial' for Fahrenheit
        }

        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx and 5xx)
            data = response.json()

            if data.get("cod") != 200:
                return f"Error fetching weather data: {data.get('message')}"

            weather_description = data["weather"][0]["description"]
            temperature = data["main"]["temp"]
            humidity = data["main"]["humidity"]
            wind_speed = data["wind"]["speed"]

            return f"Weather in {city}: {temperature}°C"
        except requests.RequestException as e:
            return f"Error fetching weather data: {str(e)}"
`;const Ee=async()=>{ke()({id:E(),name:k(),meta:T(),content:p(),access_control:j()})},Z=async()=>{if(d(P)){p(d(q)),await K();const t=await d(P).formatPythonCodeHandler();await K(),p(d(q)),await K(),t&&Ee()}};he(()=>I(p()),()=>{p()&&$e()}),he(()=>(I(k()),I(w()),I(X())),()=>{k()&&!w()&&!X()&&E(k().replace(/\s+/g,"_").toLowerCase())}),Ke(),Xe();var ee=ft(),te=ze(ee);{let t=y(()=>(x(),l(()=>{var i,s,o,f;return((o=(s=(i=x())==null?void 0:i.permissions)==null?void 0:s.sharing)==null?void 0:o.tools)||((f=x())==null?void 0:f.role)==="admin"}))),n=y(()=>(x(),l(()=>{var i,s,o,f;return((o=(s=(i=x())==null?void 0:i.permissions)==null?void 0:s.sharing)==null?void 0:o.public_tools)||((f=x())==null?void 0:f.role)==="admin"})));it(te,{accessRoles:["read","write"],get share(){return d(t)},get sharePublic(){return d(n)},get show(){return d(M)},set show(i){v(M,i)},get accessControl(){return j()},set accessControl(i){j(i)},$$legacy:!0})}var H=u(te,2),re=r(H),A=r(re),ae=r(A),S=r(ae),W=r(S),F=r(W),Te=r(F);{let t=y(()=>(e(),l(()=>e().t("Back"))));D(Te,{get content(){return d(t)},children:(n,i)=>{var s=lt(),o=r(s);st(o,{strokeWidth:"2.5"}),a(s),O("click",s,()=>{et("/workspace/tools")}),h(n,s)},$$slots:{default:!0}})}a(F);var R=u(F,2),qe=r(R);{let t=y(()=>(e(),l(()=>e().t("e.g. My Tools"))));D(qe,{get content(){return d(t)},placement:"top-start",children:(n,i)=>{var s=nt();z(s),b(o=>J(s,"placeholder",o),[()=>(e(),l(()=>e().t("Tool Name")))]),Q(s,k),h(n,s)},$$slots:{default:!0}})}a(R);var se=u(R,2),U=r(se),oe=r(U);ot(oe,{strokeWidth:"2.5",className:"size-3.5"});var ie=u(oe,2),Pe=r(ie,!0);a(ie),a(U),a(se),a(W);var le=u(W,2),ne=r(le);{var Ae=t=>{var n=dt(),i=r(n,!0);a(n),b(()=>c(i,E())),h(t,n)},Ie=t=>{{let n=y(()=>(e(),l(()=>e().t("e.g. my_tools"))));D(t,{className:"w-full",get content(){return d(n)},placement:"top-start",children:(i,s)=>{var o=ut();z(o),b(f=>{J(o,"placeholder",f),o.disabled=w()},[()=>(e(),l(()=>e().t("Tool ID")))]),Q(o,E),h(i,o)},$$slots:{default:!0}})}};Qe(ne,t=>{w()?t(Ae):t(Ie,!1)})}var De=u(ne,2);{let t=y(()=>(e(),l(()=>e().t("e.g. Tools for performing various operations"))));D(De,{className:"w-full self-center items-center flex",get content(){return d(t)},placement:"top-start",children:(n,i)=>{var s=ct();z(s),b(o=>J(s,"placeholder",o),[()=>(e(),l(()=>e().t("Tool Description")))]),Q(s,()=>T().description,o=>T(T().description=o,!0)),h(n,s)},$$slots:{default:!0}})}a(le),a(S);var Y=u(S,2),Ne=r(Y);ge(rt(Ne,{get value(){return p()},lang:"python",boilerplate:Ce,onChange:t=>{v(q,t)},onSave:async()=>{d(C)&&d(C).requestSubmit()},$$legacy:!0}),t=>v(P,t),()=>d(P)),a(Y);var de=u(Y,2),G=r(de),ue=r(G),L=r(ue),Me=r(L,!0);a(L);var ce=u(L),me=u(ce,3),je=r(me,!0);a(me),a(ue),a(G);var fe=u(G,2),He=r(fe,!0);a(fe),a(de),a(ae),a(A),ge(A,t=>v(C,t),()=>d(C)),a(re),a(H);var Se=u(H,2);at(Se,{get show(){return d(N)},set show(t){v(N,t)},$$events:{confirm:()=>{Z()}},children:(t,n)=>{var i=mt(),s=r(i),o=r(s),f=r(o,!0);a(o);var ve=u(o,2),B=r(ve),We=r(B,!0);a(B);var _e=u(B,2),Fe=r(_e,!0);a(_e),a(ve),a(s);var pe=u(s,2),Re=r(pe,!0);a(pe),a(i),b((Ue,Ye,Ge,Le)=>{c(f,Ue),c(We,Ye),c(Fe,Ge),c(Re,Le)},[()=>(e(),l(()=>e().t("Please carefully review the following warnings:"))),()=>(e(),l(()=>e().t("Tools have a function calling system that allows arbitrary code execution."))),()=>(e(),l(()=>e().t("Do not install tools from sources you do not fully trust."))),()=>(e(),l(()=>e().t("I acknowledge that I have read and I understand the implications of my action. I am aware of the risks associated with executing arbitrary code and I have verified the trustworthiness of the source.")))]),h(t,i)},$$slots:{default:!0},$$legacy:!0}),b((t,n,i,s,o)=>{c(Pe,t),c(Me,n),c(ce,` ${i??""} `),c(je,s),c(He,o)},[()=>(e(),l(()=>e().t("Access"))),()=>(e(),l(()=>e().t("Warning:"))),()=>(e(),l(()=>e().t("Tools are a function calling system with arbitrary code execution"))),()=>(e(),l(()=>e().t("don't install random tools from sources you don't trust."))),()=>(e(),l(()=>e().t("Save")))]),O("click",U,()=>{v(M,!0)}),O("submit",A,Ve(()=>{w()?Z():v(N,!0)})),h(ye,ee),Je(),be()}export{Nt as T};
//# sourceMappingURL=BwFqwAiy.js.map
