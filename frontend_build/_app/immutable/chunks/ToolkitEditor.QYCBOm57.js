import{s as nt,y as Ee,k as A,e as m,t as H,o as P,c as h,a as _,d as f,b as L,f as c,i as ee,g as n,u as he,z as lt,A as Le,h as z,H as it,p as ut,j as ct,B as ft,n as We,C as _e,D as Oe}from"./scheduler.Dg_Xn4WQ.js";import{S as dt,i as mt,f as Re,b as J,d as Q,m as X,g as ht,a as M,c as _t,t as j,e as Z}from"./index.gNonUo3Z.js";import{C as pt}from"./CodeEditor.D-leIv_8.js";import{g as gt}from"./entry.C1o6s8Km.js";import{C as vt}from"./ConfirmDialog.BuoJh2qp.js";import{C as wt}from"./ChevronLeft.DO9C7Lvo.js";import{T as Pe}from"./Tooltip.FP-CxtJW.js";import{A as bt,L as yt}from"./AccessControlModal.D5PlTLhT.js";function kt(s){let e,t,r,u,a;return t=new wt({props:{strokeWidth:"2.5"}}),{c(){e=m("button"),J(t.$$.fragment),this.h()},l(i){e=h(i,"BUTTON",{class:!0,type:!0});var p=_(e);Q(t.$$.fragment,p),p.forEach(f),this.h()},h(){c(e,"class","w-full text-left text-sm py-1.5 px-1 rounded-lg dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-gray-850"),c(e,"type","button")},m(i,p){ee(i,e,p),X(t,e,null),r=!0,u||(a=he(e,"click",s[18]),u=!0)},p:We,i(i){r||(j(t.$$.fragment,i),r=!0)},o(i){M(t.$$.fragment,i),r=!1},d(i){i&&f(e),Z(t),u=!1,a()}}}function Et(s){let e,t,r,u;return{c(){e=m("input"),this.h()},l(a){e=h(a,"INPUT",{class:!0,type:!0,placeholder:!0}),this.h()},h(){c(e,"class","w-full text-2xl font-semibold bg-transparent outline-none"),c(e,"type","text"),c(e,"placeholder",t=s[11].t("Tool Name")),e.required=!0},m(a,i){ee(a,e,i),_e(e,s[0]),r||(u=he(e,"input",s[19]),r=!0)},p(a,i){i[0]&2048&&t!==(t=a[11].t("Tool Name"))&&c(e,"placeholder",t),i[0]&1&&e.value!==a[0]&&_e(e,a[0])},d(a){a&&f(e),r=!1,u()}}}function It(s){let e,t;return e=new Pe({props:{className:"w-full",content:s[11].t("e.g. my_tools"),placement:"top-start",$$slots:{default:[Dt]},$$scope:{ctx:s}}}),{c(){J(e.$$.fragment)},l(r){Q(e.$$.fragment,r)},m(r,u){X(e,r,u),t=!0},p(r,u){const a={};u[0]&2048&&(a.content=r[11].t("e.g. my_tools")),u[0]&2084|u[1]&8&&(a.$$scope={dirty:u,ctx:r}),e.$set(a)},i(r){t||(j(e.$$.fragment,r),t=!0)},o(r){M(e.$$.fragment,r),t=!1},d(r){Z(e,r)}}}function Tt(s){let e,t;return{c(){e=m("div"),t=H(s[2]),this.h()},l(r){e=h(r,"DIV",{class:!0});var u=_(e);t=L(u,s[2]),u.forEach(f),this.h()},h(){c(e,"class","text-sm text-gray-500 flex-shrink-0")},m(r,u){ee(r,e,u),n(e,t)},p(r,u){u[0]&4&&z(t,r[2])},i:We,o:We,d(r){r&&f(e)}}}function Dt(s){let e,t,r,u;return{c(){e=m("input"),this.h()},l(a){e=h(a,"INPUT",{class:!0,type:!0,placeholder:!0}),this.h()},h(){c(e,"class","w-full text-sm disabled:text-gray-500 bg-transparent outline-none"),c(e,"type","text"),c(e,"placeholder",t=s[11].t("Tool ID")),e.required=!0,e.disabled=s[5]},m(a,i){ee(a,e,i),_e(e,s[2]),r||(u=he(e,"input",s[21]),r=!0)},p(a,i){i[0]&2048&&t!==(t=a[11].t("Tool ID"))&&c(e,"placeholder",t),i[0]&32&&(e.disabled=a[5]),i[0]&4&&e.value!==a[2]&&_e(e,a[2])},d(a){a&&f(e),r=!1,u()}}}function Ct(s){let e,t,r,u;return{c(){e=m("input"),this.h()},l(a){e=h(a,"INPUT",{class:!0,type:!0,placeholder:!0}),this.h()},h(){c(e,"class","w-full text-sm bg-transparent outline-none"),c(e,"type","text"),c(e,"placeholder",t=s[11].t("Tool Description")),e.required=!0},m(a,i){ee(a,e,i),_e(e,s[3].description),r||(u=he(e,"input",s[22]),r=!0)},p(a,i){i[0]&2048&&t!==(t=a[11].t("Tool Description"))&&c(e,"placeholder",t),i[0]&8&&e.value!==a[3].description&&_e(e,a[3].description)},d(a){a&&f(e),r=!1,u()}}}function $t(s){let e,t,r,u=s[11].t("Please carefully review the following warnings:")+"",a,i,p,v,b=s[11].t("Tools have a function calling system that allows arbitrary code execution.")+"",y,T,g,V=s[11].t("Do not install tools from sources you do not fully trust.")+"",E,I,$,N=s[11].t("I acknowledge that I have read and I understand the implications of my action. I am aware of the risks associated with executing arbitrary code and I have verified the trustworthiness of the source.")+"",w;return{c(){e=m("div"),t=m("div"),r=m("div"),a=H(u),i=A(),p=m("ul"),v=m("li"),y=H(b),T=A(),g=m("li"),E=H(V),I=A(),$=m("div"),w=H(N),this.h()},l(k){e=h(k,"DIV",{class:!0});var D=_(e);t=h(D,"DIV",{class:!0});var q=_(t);r=h(q,"DIV",{});var O=_(r);a=L(O,u),O.forEach(f),i=P(q),p=h(q,"UL",{class:!0});var B=_(p);v=h(B,"LI",{});var te=_(v);y=L(te,b),te.forEach(f),T=P(B),g=h(B,"LI",{});var U=_(g);E=L(U,V),U.forEach(f),B.forEach(f),q.forEach(f),I=P(D),$=h(D,"DIV",{class:!0});var C=_($);w=L(C,N),C.forEach(f),D.forEach(f),this.h()},h(){c(p,"class","mt-1 list-disc pl-4 text-xs"),c(t,"class","bg-yellow-500/20 text-yellow-700 dark:text-yellow-200 rounded-lg px-4 py-3"),c($,"class","my-3"),c(e,"class","text-sm text-gray-500")},m(k,D){ee(k,e,D),n(e,t),n(t,r),n(r,a),n(t,i),n(t,p),n(p,v),n(v,y),n(p,T),n(p,g),n(g,E),n(e,I),n(e,$),n($,w)},p(k,D){D[0]&2048&&u!==(u=k[11].t("Please carefully review the following warnings:")+"")&&z(a,u),D[0]&2048&&b!==(b=k[11].t("Tools have a function calling system that allows arbitrary code execution.")+"")&&z(y,b),D[0]&2048&&V!==(V=k[11].t("Do not install tools from sources you do not fully trust.")+"")&&z(E,V),D[0]&2048&&N!==(N=k[11].t("I acknowledge that I have read and I understand the implications of my action. I am aware of the risks associated with executing arbitrary code and I have verified the trustworthiness of the source.")+"")&&z(w,N)},d(k){k&&f(e)}}}function Vt(s){let e,t,r,u,a,i,p,v,b,y,T,g,V,E,I,$,N,w,k,D,q,O=s[11].t("Access")+"",B,te,U,C,S,ie,R,pe,se,x,ge,W,oe,l,ue,ve=s[11].t("Warning:")+"",Ie,Ne,we=s[11].t("Tools are a function calling system with arbitrary code execution")+"",Te,Ue,Se,xe,ce,be=s[11].t("don't install random tools from sources you don't trust.")+"",De,Be,le,ye=s[11].t("Save")+"",Ce,$e,F,Me,K,je,Fe;function st(o){s[16](o)}function ot(o){s[17](o)}let He={accessRoles:["read","write"]};s[8]!==void 0&&(He.show=s[8]),s[4]!==void 0&&(He.accessControl=s[4]),e=new bt({props:He}),Ee.push(()=>Re(e,"show",st)),Ee.push(()=>Re(e,"accessControl",ot)),g=new Pe({props:{content:s[11].t("Back"),$$slots:{default:[kt]},$$scope:{ctx:s}}}),I=new Pe({props:{content:s[11].t("e.g. My Tools"),placement:"top-start",$$slots:{default:[Et]},$$scope:{ctx:s}}}),k=new yt({props:{strokeWidth:"2.5",className:"size-3.5"}});const Ge=[Tt,It],ae=[];function Ye(o,d){return o[5]?0:1}C=Ye(s),S=ae[C]=Ge[C](s),R=new Pe({props:{className:"w-full self-center items-center flex",content:s[11].t("e.g. Tools for performing various operations"),placement:"top-start",$$slots:{default:[Ct]},$$scope:{ctx:s}}});let at={value:s[1],boilerplate:s[13],lang:"python"};x=new pt({props:at}),s[23](x),x.$on("change",s[24]),x.$on("save",s[25]);function rt(o){s[28](o)}let ze={$$slots:{default:[$t]},$$scope:{ctx:s}};return s[7]!==void 0&&(ze.show=s[7]),F=new vt({props:ze}),Ee.push(()=>Re(F,"show",rt)),F.$on("confirm",s[29]),{c(){J(e.$$.fragment),u=A(),a=m("div"),i=m("div"),p=m("form"),v=m("div"),b=m("div"),y=m("div"),T=m("div"),J(g.$$.fragment),V=A(),E=m("div"),J(I.$$.fragment),$=A(),N=m("div"),w=m("button"),J(k.$$.fragment),D=A(),q=m("div"),B=H(O),te=A(),U=m("div"),S.c(),ie=A(),J(R.$$.fragment),pe=A(),se=m("div"),J(x.$$.fragment),ge=A(),W=m("div"),oe=m("div"),l=m("div"),ue=m("span"),Ie=H(ve),Ne=A(),Te=H(we),Ue=A(),Se=m("br"),xe=H(`—
							`),ce=m("span"),De=H(be),Be=A(),le=m("button"),Ce=H(ye),$e=A(),J(F.$$.fragment),this.h()},l(o){Q(e.$$.fragment,o),u=P(o),a=h(o,"DIV",{class:!0});var d=_(a);i=h(d,"DIV",{class:!0});var fe=_(i);p=h(fe,"FORM",{class:!0});var de=_(p);v=h(de,"DIV",{class:!0});var G=_(v);b=h(G,"DIV",{class:!0});var re=_(b);y=h(re,"DIV",{class:!0});var Y=_(y);T=h(Y,"DIV",{class:!0});var ke=_(T);Q(g.$$.fragment,ke),ke.forEach(f),V=P(Y),E=h(Y,"DIV",{class:!0});var me=_(E);Q(I.$$.fragment,me),me.forEach(f),$=P(Y),N=h(Y,"DIV",{class:!0});var Ke=_(N);w=h(Ke,"BUTTON",{class:!0,type:!0});var Ve=_(w);Q(k.$$.fragment,Ve),D=P(Ve),q=h(Ve,"DIV",{class:!0});var Je=_(q);B=L(Je,O),Je.forEach(f),Ve.forEach(f),Ke.forEach(f),Y.forEach(f),te=P(re),U=h(re,"DIV",{class:!0});var qe=_(U);S.l(qe),ie=P(qe),Q(R.$$.fragment,qe),qe.forEach(f),re.forEach(f),pe=P(G),se=h(G,"DIV",{class:!0});var Qe=_(se);Q(x.$$.fragment,Qe),Qe.forEach(f),ge=P(G),W=h(G,"DIV",{class:!0});var Ae=_(W);oe=h(Ae,"DIV",{class:!0});var Xe=_(oe);l=h(Xe,"DIV",{class:!0});var ne=_(l);ue=h(ne,"SPAN",{class:!0});var Ze=_(ue);Ie=L(Ze,ve),Ze.forEach(f),Ne=P(ne),Te=L(ne,we),Ue=P(ne),Se=h(ne,"BR",{}),xe=L(ne,`—
							`),ce=h(ne,"SPAN",{class:!0});var et=_(ce);De=L(et,be),et.forEach(f),ne.forEach(f),Xe.forEach(f),Be=P(Ae),le=h(Ae,"BUTTON",{class:!0,type:!0});var tt=_(le);Ce=L(tt,ye),tt.forEach(f),Ae.forEach(f),G.forEach(f),de.forEach(f),fe.forEach(f),d.forEach(f),$e=P(o),Q(F.$$.fragment,o),this.h()},h(){c(T,"class","flex-shrink-0 mr-2"),c(E,"class","flex-1"),c(q,"class","text-sm font-medium flex-shrink-0"),c(w,"class","bg-gray-50 hover:bg-gray-100 text-black dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-white transition px-2 py-1 rounded-full flex gap-1 items-center"),c(w,"type","button"),c(N,"class","self-center flex-shrink-0"),c(y,"class","flex w-full items-center"),c(U,"class","flex gap-2 px-1 items-center"),c(b,"class","w-full mb-2 flex flex-col gap-0.5"),c(se,"class","mb-2 flex-1 overflow-auto h-0 rounded-lg"),c(ue,"class","font-semibold dark:text-gray-200"),c(ce,"class","font-medium dark:text-gray-400"),c(l,"class","text-xs text-gray-500 line-clamp-2"),c(oe,"class","flex-1 pr-3"),c(le,"class","px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"),c(le,"type","submit"),c(W,"class","pb-3 flex justify-between"),c(v,"class","flex flex-col flex-1 overflow-auto h-0"),c(p,"class","flex flex-col max-h-[100dvh] h-full"),c(i,"class","mx-auto w-full md:px-0 h-full"),c(a,"class","flex flex-col justify-between w-full overflow-y-auto h-full")},m(o,d){X(e,o,d),ee(o,u,d),ee(o,a,d),n(a,i),n(i,p),n(p,v),n(v,b),n(b,y),n(y,T),X(g,T,null),n(y,V),n(y,E),X(I,E,null),n(y,$),n(y,N),n(N,w),X(k,w,null),n(w,D),n(w,q),n(q,B),n(b,te),n(b,U),ae[C].m(U,null),n(U,ie),X(R,U,null),n(v,pe),n(v,se),X(x,se,null),n(v,ge),n(v,W),n(W,oe),n(oe,l),n(l,ue),n(ue,Ie),n(l,Ne),n(l,Te),n(l,Ue),n(l,Se),n(l,xe),n(l,ce),n(ce,De),n(W,Be),n(W,le),n(le,Ce),s[26](p),ee(o,$e,d),X(F,o,d),K=!0,je||(Fe=[he(w,"click",s[20]),he(p,"submit",lt(s[27]))],je=!0)},p(o,d){const fe={};!t&&d[0]&256&&(t=!0,fe.show=o[8],Le(()=>t=!1)),!r&&d[0]&16&&(r=!0,fe.accessControl=o[4],Le(()=>r=!1)),e.$set(fe);const de={};d[0]&2048&&(de.content=o[11].t("Back")),d[1]&8&&(de.$$scope={dirty:d,ctx:o}),g.$set(de);const G={};d[0]&2048&&(G.content=o[11].t("e.g. My Tools")),d[0]&2049|d[1]&8&&(G.$$scope={dirty:d,ctx:o}),I.$set(G),(!K||d[0]&2048)&&O!==(O=o[11].t("Access")+"")&&z(B,O);let re=C;C=Ye(o),C===re?ae[C].p(o,d):(ht(),M(ae[re],1,1,()=>{ae[re]=null}),_t(),S=ae[C],S?S.p(o,d):(S=ae[C]=Ge[C](o),S.c()),j(S,1),S.m(U,ie));const Y={};d[0]&2048&&(Y.content=o[11].t("e.g. Tools for performing various operations")),d[0]&2056|d[1]&8&&(Y.$$scope={dirty:d,ctx:o}),R.$set(Y);const ke={};d[0]&2&&(ke.value=o[1]),x.$set(ke),(!K||d[0]&2048)&&ve!==(ve=o[11].t("Warning:")+"")&&z(Ie,ve),(!K||d[0]&2048)&&we!==(we=o[11].t("Tools are a function calling system with arbitrary code execution")+"")&&z(Te,we),(!K||d[0]&2048)&&be!==(be=o[11].t("don't install random tools from sources you don't trust.")+"")&&z(De,be),(!K||d[0]&2048)&&ye!==(ye=o[11].t("Save")+"")&&z(Ce,ye);const me={};d[0]&2048|d[1]&8&&(me.$$scope={dirty:d,ctx:o}),!Me&&d[0]&128&&(Me=!0,me.show=o[7],Le(()=>Me=!1)),F.$set(me)},i(o){K||(j(e.$$.fragment,o),j(g.$$.fragment,o),j(I.$$.fragment,o),j(k.$$.fragment,o),j(S),j(R.$$.fragment,o),j(x.$$.fragment,o),j(F.$$.fragment,o),K=!0)},o(o){M(e.$$.fragment,o),M(g.$$.fragment,o),M(I.$$.fragment,o),M(k.$$.fragment,o),M(S),M(R.$$.fragment,o),M(x.$$.fragment,o),M(F.$$.fragment,o),K=!1},d(o){o&&(f(u),f(a),f($e)),Z(e,o),Z(g),Z(I),Z(k),ae[C].d(),Z(R),s[23](null),Z(x),s[26](null),Z(F,o),je=!1,it(Fe)}}}function qt(s,e,t){let r;const u=ut("i18n");ct(s,u,l=>t(11,r=l));const a=ft();let i=null,p=!1,v=!1,{edit:b=!1}=e,{clone:y=!1}=e,{id:T=""}=e,{name:g=""}=e,{meta:V={description:""}}=e,{content:E=""}=e,{accessControl:I=null}=e,$="";const N=()=>{t(9,$=E)};let w,k=`import os
import requests
from datetime import datetime


class Tools:
    def __init__(self):
        pass

    # Add your custom tools using pure Python code here, make sure to add type hints
    # Use Sphinx-style docstrings to document your tools, they will be used for generating tools specifications
    # Please refer to function_calling_filter_pipeline.py file from pipelines project for an example

    def get_user_name_and_email_and_id(self, __user__: dict = {}) -> str:
        """
        Get the user name, Email and ID from the user object.
        """

        # Do not include :param for __user__ in the docstring as it should not be shown in the tool's specification
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
        :return: The current time.
        """

        now = datetime.now()
        current_time = now.strftime("%I:%M:%S %p")  # Using 12-hour format with AM/PM
        current_date = now.strftime(
            "%A, %B %d, %Y"
        )  # Full weekday, month name, day, and year

        return f"Current Date and Time = {current_date}, {current_time}"

    def calculator(self, equation: str) -> str:
        """
        Calculate the result of an equation.
        :param equation: The equation to calculate.
        """

        # Avoid using eval in production code
        # https://nedbatchelder.com/blog/201206/eval_really_is_dangerous.html
        try:
            result = eval(equation)
            return f"{equation} = {result}"
        except Exception as e:
            print(e)
            return "Invalid equation"

    def get_current_weather(self, city: str) -> str:
        """
        Get the current weather for a given city.
        :param city: The name of the city to get the weather for.
        :return: The current weather information or an error message.
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
`;const D=async()=>{a("save",{id:T,name:g,meta:V,content:E,access_control:I})},q=async()=>{if(w){t(1,E=$),await Oe();const l=await w.formatPythonCodeHandler();await Oe(),t(1,E=$),await Oe(),l&&(console.log("Code formatted successfully"),D())}};function O(l){v=l,t(8,v)}function B(l){I=l,t(4,I)}const te=()=>{gt("/workspace/tools")};function U(){g=this.value,t(0,g)}const C=()=>{t(8,v=!0)};function S(){T=this.value,t(2,T),t(0,g),t(5,b),t(15,y)}function ie(){V.description=this.value,t(3,V)}function R(l){Ee[l?"unshift":"push"](()=>{w=l,t(10,w)})}const pe=l=>{t(9,$=l.detail.value)},se=()=>{i&&i.requestSubmit()};function x(l){Ee[l?"unshift":"push"](()=>{i=l,t(6,i)})}const ge=()=>{b?q():t(7,p=!0)};function W(l){p=l,t(7,p)}const oe=()=>{q()};return s.$$set=l=>{"edit"in l&&t(5,b=l.edit),"clone"in l&&t(15,y=l.clone),"id"in l&&t(2,T=l.id),"name"in l&&t(0,g=l.name),"meta"in l&&t(3,V=l.meta),"content"in l&&t(1,E=l.content),"accessControl"in l&&t(4,I=l.accessControl)},s.$$.update=()=>{s.$$.dirty[0]&2&&E&&N(),s.$$.dirty[0]&32801&&g&&!b&&!y&&t(2,T=g.replace(/\s+/g,"_").toLowerCase())},[g,E,T,V,I,b,i,p,v,$,w,r,u,k,q,y,O,B,te,U,C,S,ie,R,pe,se,x,ge,W,oe]}class jt extends dt{constructor(e){super(),mt(this,e,qt,Vt,nt,{edit:5,clone:15,id:2,name:0,meta:3,content:1,accessControl:4},null,[-1,-1])}}export{jt as T};
//# sourceMappingURL=ToolkitEditor.QYCBOm57.js.map
