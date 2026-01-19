import{_ as c,g as ke,s as ye,q as ge,p as pe,a as ve,b as Te,c as lt,d as xe,l as st,j as be,i as we,y as _e,u as De}from"./BTaIz8BB.js";import{c as Lt,g as Yt,d as j}from"./BC4znSyB.js";import{d as Se}from"./DfIywdCw.js";import{s as pt}from"./CxNpLfvs.js";import{t as Ce,m as Ee,a as Me,i as Ie,b as $t,c as jt,d as Ae,e as Fe,f as Le,g as Ye,h as We,j as Oe,k as Ve,l as qt,n as Ut,o as Zt,s as Qt,p as Kt}from"./Di3Ls8bK.js";import{l as ze}from"./39BZt47D.js";function Pe(t){return t}var Tt=1,St=2,Et=3,vt=4,Jt=1e-6;function Ne(t){return"translate("+t+",0)"}function Re(t){return"translate(0,"+t+")"}function Be(t){return i=>+t(i)}function He(t,i){return i=Math.max(0,t.bandwidth()-i*2)/2,t.round()&&(i=Math.round(i)),n=>+t(n)+i}function Ge(){return!this.__axis}function ie(t,i){var n=[],s=null,a=null,h=6,u=6,v=3,D=typeof window<"u"&&window.devicePixelRatio>1?0:.5,E=t===Tt||t===vt?-1:1,g=t===vt||t===St?"x":"y",L=t===Tt||t===Et?Ne:Re;function S(w){var G=s??(i.ticks?i.ticks.apply(i,n):i.domain()),I=a??(i.tickFormat?i.tickFormat.apply(i,n):Pe),_=Math.max(h,0)+v,M=i.range(),W=+M[0]+D,O=+M[M.length-1]+D,P=(i.bandwidth?He:Be)(i.copy(),D),N=w.selection?w.selection():w,X=N.selectAll(".domain").data([null]),z=N.selectAll(".tick").data(G,i).order(),R=z.exit(),k=z.enter().append("g").attr("class","tick"),x=z.select("line"),b=z.select("text");X=X.merge(X.enter().insert("path",".tick").attr("class","domain").attr("stroke","currentColor")),z=z.merge(k),x=x.merge(k.append("line").attr("stroke","currentColor").attr(g+"2",E*h)),b=b.merge(k.append("text").attr("fill","currentColor").attr(g,E*_).attr("dy",t===Tt?"0em":t===Et?"0.71em":"0.32em")),w!==N&&(X=X.transition(w),z=z.transition(w),x=x.transition(w),b=b.transition(w),R=R.transition(w).attr("opacity",Jt).attr("transform",function(y){return isFinite(y=P(y))?L(y+D):this.getAttribute("transform")}),k.attr("opacity",Jt).attr("transform",function(y){var m=this.parentNode.__axis;return L((m&&isFinite(m=m(y))?m:P(y))+D)})),R.remove(),X.attr("d",t===vt||t===St?u?"M"+E*u+","+W+"H"+D+"V"+O+"H"+E*u:"M"+D+","+W+"V"+O:u?"M"+W+","+E*u+"V"+D+"H"+O+"V"+E*u:"M"+W+","+D+"H"+O),z.attr("opacity",1).attr("transform",function(y){return L(P(y)+D)}),x.attr(g+"2",E*h),b.attr(g,E*_).text(I),N.filter(Ge).attr("fill","none").attr("font-size",10).attr("font-family","sans-serif").attr("text-anchor",t===St?"start":t===vt?"end":"middle"),N.each(function(){this.__axis=P})}return S.scale=function(w){return arguments.length?(i=w,S):i},S.ticks=function(){return n=Array.from(arguments),S},S.tickArguments=function(w){return arguments.length?(n=w==null?[]:Array.from(w),S):n.slice()},S.tickValues=function(w){return arguments.length?(s=w==null?null:Array.from(w),S):s&&s.slice()},S.tickFormat=function(w){return arguments.length?(a=w,S):a},S.tickSize=function(w){return arguments.length?(h=u=+w,S):h},S.tickSizeInner=function(w){return arguments.length?(h=+w,S):h},S.tickSizeOuter=function(w){return arguments.length?(u=+w,S):u},S.tickPadding=function(w){return arguments.length?(v=+w,S):v},S.offset=function(w){return arguments.length?(D=+w,S):D},S}function Xe(t){return ie(Tt,t)}function $e(t){return ie(Et,t)}var ne={exports:{}};(function(t,i){(function(n,s){t.exports=s()})(Lt,function(){var n="day";return function(s,a,h){var u=function(E){return E.add(4-E.isoWeekday(),n)},v=a.prototype;v.isoWeekYear=function(){return u(this).year()},v.isoWeek=function(E){if(!this.$utils().u(E))return this.add(7*(E-this.isoWeek()),n);var g,L,S,w,G=u(this),I=(g=this.isoWeekYear(),L=this.$u,S=(L?h.utc:h)().year(g).startOf("year"),w=4-S.isoWeekday(),S.isoWeekday()>4&&(w+=7),S.add(w,n));return G.diff(I,"week")+1},v.isoWeekday=function(E){return this.$utils().u(E)?this.day()||7:this.day(this.day()%7?E:E-7)};var D=v.startOf;v.startOf=function(E,g){var L=this.$utils(),S=!!L.u(g)||g;return L.p(E)==="isoweek"?S?this.date(this.date()-(this.isoWeekday()-1)).startOf("day"):this.date(this.date()-1-(this.isoWeekday()-1)+7).endOf("day"):D.bind(this)(E,g)}}})})(ne);var je=ne.exports;const qe=Yt(je);var se={exports:{}};(function(t,i){(function(n,s){t.exports=s()})(Lt,function(){var n={LTS:"h:mm:ss A",LT:"h:mm A",L:"MM/DD/YYYY",LL:"MMMM D, YYYY",LLL:"MMMM D, YYYY h:mm A",LLLL:"dddd, MMMM D, YYYY h:mm A"},s=/(\[[^[]*\])|([-_:/.,()\s]+)|(A|a|Q|YYYY|YY?|ww?|MM?M?M?|Do|DD?|hh?|HH?|mm?|ss?|S{1,3}|z|ZZ?)/g,a=/\d/,h=/\d\d/,u=/\d\d?/,v=/\d*[^-_:/,()\s\d]+/,D={},E=function(_){return(_=+_)+(_>68?1900:2e3)},g=function(_){return function(M){this[_]=+M}},L=[/[+-]\d\d:?(\d\d)?|Z/,function(_){(this.zone||(this.zone={})).offset=function(M){if(!M||M==="Z")return 0;var W=M.match(/([+-]|\d\d)/g),O=60*W[1]+(+W[2]||0);return O===0?0:W[0]==="+"?-O:O}(_)}],S=function(_){var M=D[_];return M&&(M.indexOf?M:M.s.concat(M.f))},w=function(_,M){var W,O=D.meridiem;if(O){for(var P=1;P<=24;P+=1)if(_.indexOf(O(P,0,M))>-1){W=P>12;break}}else W=_===(M?"pm":"PM");return W},G={A:[v,function(_){this.afternoon=w(_,!1)}],a:[v,function(_){this.afternoon=w(_,!0)}],Q:[a,function(_){this.month=3*(_-1)+1}],S:[a,function(_){this.milliseconds=100*+_}],SS:[h,function(_){this.milliseconds=10*+_}],SSS:[/\d{3}/,function(_){this.milliseconds=+_}],s:[u,g("seconds")],ss:[u,g("seconds")],m:[u,g("minutes")],mm:[u,g("minutes")],H:[u,g("hours")],h:[u,g("hours")],HH:[u,g("hours")],hh:[u,g("hours")],D:[u,g("day")],DD:[h,g("day")],Do:[v,function(_){var M=D.ordinal,W=_.match(/\d+/);if(this.day=W[0],M)for(var O=1;O<=31;O+=1)M(O).replace(/\[|\]/g,"")===_&&(this.day=O)}],w:[u,g("week")],ww:[h,g("week")],M:[u,g("month")],MM:[h,g("month")],MMM:[v,function(_){var M=S("months"),W=(S("monthsShort")||M.map(function(O){return O.slice(0,3)})).indexOf(_)+1;if(W<1)throw new Error;this.month=W%12||W}],MMMM:[v,function(_){var M=S("months").indexOf(_)+1;if(M<1)throw new Error;this.month=M%12||M}],Y:[/[+-]?\d+/,g("year")],YY:[h,function(_){this.year=E(_)}],YYYY:[/\d{4}/,g("year")],Z:L,ZZ:L};function I(_){var M,W;M=_,W=D&&D.formats;for(var O=(_=M.replace(/(\[[^\]]+])|(LTS?|l{1,4}|L{1,4})/g,function(x,b,y){var m=y&&y.toUpperCase();return b||W[y]||n[y]||W[m].replace(/(\[[^\]]+])|(MMMM|MM|DD|dddd)/g,function(o,l,d){return l||d.slice(1)})})).match(s),P=O.length,N=0;N<P;N+=1){var X=O[N],z=G[X],R=z&&z[0],k=z&&z[1];O[N]=k?{regex:R,parser:k}:X.replace(/^\[|\]$/g,"")}return function(x){for(var b={},y=0,m=0;y<P;y+=1){var o=O[y];if(typeof o=="string")m+=o.length;else{var l=o.regex,d=o.parser,f=x.slice(m),T=l.exec(f)[0];d.call(b,T),x=x.replace(T,"")}}return function(r){var V=r.afternoon;if(V!==void 0){var e=r.hours;V?e<12&&(r.hours+=12):e===12&&(r.hours=0),delete r.afternoon}}(b),b}}return function(_,M,W){W.p.customParseFormat=!0,_&&_.parseTwoDigitYear&&(E=_.parseTwoDigitYear);var O=M.prototype,P=O.parse;O.parse=function(N){var X=N.date,z=N.utc,R=N.args;this.$u=z;var k=R[1];if(typeof k=="string"){var x=R[2]===!0,b=R[3]===!0,y=x||b,m=R[2];b&&(m=R[2]),D=this.$locale(),!x&&m&&(D=W.Ls[m]),this.$d=function(f,T,r,V){try{if(["x","X"].indexOf(T)>-1)return new Date((T==="X"?1e3:1)*f);var e=I(T)(f),p=e.year,Y=e.month,F=e.day,A=e.hours,$=e.minutes,C=e.seconds,Q=e.milliseconds,rt=e.zone,ot=e.week,ft=new Date,ht=F||(p||Y?1:ft.getDate()),ct=p||ft.getFullYear(),B=0;p&&!Y||(B=Y>0?Y-1:ft.getMonth());var Z,q=A||0,nt=$||0,K=C||0,it=Q||0;return rt?new Date(Date.UTC(ct,B,ht,q,nt,K,it+60*rt.offset*1e3)):r?new Date(Date.UTC(ct,B,ht,q,nt,K,it)):(Z=new Date(ct,B,ht,q,nt,K,it),ot&&(Z=V(Z).week(ot).toDate()),Z)}catch{return new Date("")}}(X,k,z,W),this.init(),m&&m!==!0&&(this.$L=this.locale(m).$L),y&&X!=this.format(k)&&(this.$d=new Date("")),D={}}else if(k instanceof Array)for(var o=k.length,l=1;l<=o;l+=1){R[1]=k[l-1];var d=W.apply(this,R);if(d.isValid()){this.$d=d.$d,this.$L=d.$L,this.init();break}l===o&&(this.$d=new Date(""))}else P.call(this,N)}}})})(se);var Ue=se.exports;const Ze=Yt(Ue);var ae={exports:{}};(function(t,i){(function(n,s){t.exports=s()})(Lt,function(){return function(n,s){var a=s.prototype,h=a.format;a.format=function(u){var v=this,D=this.$locale();if(!this.isValid())return h.bind(this)(u);var E=this.$utils(),g=(u||"YYYY-MM-DDTHH:mm:ssZ").replace(/\[([^\]]+)]|Q|wo|ww|w|WW|W|zzz|z|gggg|GGGG|Do|X|x|k{1,2}|S/g,function(L){switch(L){case"Q":return Math.ceil((v.$M+1)/3);case"Do":return D.ordinal(v.$D);case"gggg":return v.weekYear();case"GGGG":return v.isoWeekYear();case"wo":return D.ordinal(v.week(),"W");case"w":case"ww":return E.s(v.week(),L==="w"?1:2,"0");case"W":case"WW":return E.s(v.isoWeek(),L==="W"?1:2,"0");case"k":case"kk":return E.s(String(v.$H===0?24:v.$H),L==="k"?1:2,"0");case"X":return Math.floor(v.$d.getTime()/1e3);case"x":return v.$d.getTime();case"z":return"["+v.offsetName()+"]";case"zzz":return"["+v.offsetName("long")+"]";default:return L}});return h.bind(this)(g)}}})})(ae);var Qe=ae.exports;const Ke=Yt(Qe);var Mt=function(){var t=c(function(m,o,l,d){for(l=l||{},d=m.length;d--;l[m[d]]=o);return l},"o"),i=[6,8,10,12,13,14,15,16,17,18,20,21,22,23,24,25,26,27,28,29,30,31,33,35,36,38,40],n=[1,26],s=[1,27],a=[1,28],h=[1,29],u=[1,30],v=[1,31],D=[1,32],E=[1,33],g=[1,34],L=[1,9],S=[1,10],w=[1,11],G=[1,12],I=[1,13],_=[1,14],M=[1,15],W=[1,16],O=[1,19],P=[1,20],N=[1,21],X=[1,22],z=[1,23],R=[1,25],k=[1,35],x={trace:c(function(){},"trace"),yy:{},symbols_:{error:2,start:3,gantt:4,document:5,EOF:6,line:7,SPACE:8,statement:9,NL:10,weekday:11,weekday_monday:12,weekday_tuesday:13,weekday_wednesday:14,weekday_thursday:15,weekday_friday:16,weekday_saturday:17,weekday_sunday:18,weekend:19,weekend_friday:20,weekend_saturday:21,dateFormat:22,inclusiveEndDates:23,topAxis:24,axisFormat:25,tickInterval:26,excludes:27,includes:28,todayMarker:29,title:30,acc_title:31,acc_title_value:32,acc_descr:33,acc_descr_value:34,acc_descr_multiline_value:35,section:36,clickStatement:37,taskTxt:38,taskData:39,click:40,callbackname:41,callbackargs:42,href:43,clickStatementDebug:44,$accept:0,$end:1},terminals_:{2:"error",4:"gantt",6:"EOF",8:"SPACE",10:"NL",12:"weekday_monday",13:"weekday_tuesday",14:"weekday_wednesday",15:"weekday_thursday",16:"weekday_friday",17:"weekday_saturday",18:"weekday_sunday",20:"weekend_friday",21:"weekend_saturday",22:"dateFormat",23:"inclusiveEndDates",24:"topAxis",25:"axisFormat",26:"tickInterval",27:"excludes",28:"includes",29:"todayMarker",30:"title",31:"acc_title",32:"acc_title_value",33:"acc_descr",34:"acc_descr_value",35:"acc_descr_multiline_value",36:"section",38:"taskTxt",39:"taskData",40:"click",41:"callbackname",42:"callbackargs",43:"href"},productions_:[0,[3,3],[5,0],[5,2],[7,2],[7,1],[7,1],[7,1],[11,1],[11,1],[11,1],[11,1],[11,1],[11,1],[11,1],[19,1],[19,1],[9,1],[9,1],[9,1],[9,1],[9,1],[9,1],[9,1],[9,1],[9,1],[9,1],[9,1],[9,2],[9,2],[9,1],[9,1],[9,1],[9,2],[37,2],[37,3],[37,3],[37,4],[37,3],[37,4],[37,2],[44,2],[44,3],[44,3],[44,4],[44,3],[44,4],[44,2]],performAction:c(function(o,l,d,f,T,r,V){var e=r.length-1;switch(T){case 1:return r[e-1];case 2:this.$=[];break;case 3:r[e-1].push(r[e]),this.$=r[e-1];break;case 4:case 5:this.$=r[e];break;case 6:case 7:this.$=[];break;case 8:f.setWeekday("monday");break;case 9:f.setWeekday("tuesday");break;case 10:f.setWeekday("wednesday");break;case 11:f.setWeekday("thursday");break;case 12:f.setWeekday("friday");break;case 13:f.setWeekday("saturday");break;case 14:f.setWeekday("sunday");break;case 15:f.setWeekend("friday");break;case 16:f.setWeekend("saturday");break;case 17:f.setDateFormat(r[e].substr(11)),this.$=r[e].substr(11);break;case 18:f.enableInclusiveEndDates(),this.$=r[e].substr(18);break;case 19:f.TopAxis(),this.$=r[e].substr(8);break;case 20:f.setAxisFormat(r[e].substr(11)),this.$=r[e].substr(11);break;case 21:f.setTickInterval(r[e].substr(13)),this.$=r[e].substr(13);break;case 22:f.setExcludes(r[e].substr(9)),this.$=r[e].substr(9);break;case 23:f.setIncludes(r[e].substr(9)),this.$=r[e].substr(9);break;case 24:f.setTodayMarker(r[e].substr(12)),this.$=r[e].substr(12);break;case 27:f.setDiagramTitle(r[e].substr(6)),this.$=r[e].substr(6);break;case 28:this.$=r[e].trim(),f.setAccTitle(this.$);break;case 29:case 30:this.$=r[e].trim(),f.setAccDescription(this.$);break;case 31:f.addSection(r[e].substr(8)),this.$=r[e].substr(8);break;case 33:f.addTask(r[e-1],r[e]),this.$="task";break;case 34:this.$=r[e-1],f.setClickEvent(r[e-1],r[e],null);break;case 35:this.$=r[e-2],f.setClickEvent(r[e-2],r[e-1],r[e]);break;case 36:this.$=r[e-2],f.setClickEvent(r[e-2],r[e-1],null),f.setLink(r[e-2],r[e]);break;case 37:this.$=r[e-3],f.setClickEvent(r[e-3],r[e-2],r[e-1]),f.setLink(r[e-3],r[e]);break;case 38:this.$=r[e-2],f.setClickEvent(r[e-2],r[e],null),f.setLink(r[e-2],r[e-1]);break;case 39:this.$=r[e-3],f.setClickEvent(r[e-3],r[e-1],r[e]),f.setLink(r[e-3],r[e-2]);break;case 40:this.$=r[e-1],f.setLink(r[e-1],r[e]);break;case 41:case 47:this.$=r[e-1]+" "+r[e];break;case 42:case 43:case 45:this.$=r[e-2]+" "+r[e-1]+" "+r[e];break;case 44:case 46:this.$=r[e-3]+" "+r[e-2]+" "+r[e-1]+" "+r[e];break}},"anonymous"),table:[{3:1,4:[1,2]},{1:[3]},t(i,[2,2],{5:3}),{6:[1,4],7:5,8:[1,6],9:7,10:[1,8],11:17,12:n,13:s,14:a,15:h,16:u,17:v,18:D,19:18,20:E,21:g,22:L,23:S,24:w,25:G,26:I,27:_,28:M,29:W,30:O,31:P,33:N,35:X,36:z,37:24,38:R,40:k},t(i,[2,7],{1:[2,1]}),t(i,[2,3]),{9:36,11:17,12:n,13:s,14:a,15:h,16:u,17:v,18:D,19:18,20:E,21:g,22:L,23:S,24:w,25:G,26:I,27:_,28:M,29:W,30:O,31:P,33:N,35:X,36:z,37:24,38:R,40:k},t(i,[2,5]),t(i,[2,6]),t(i,[2,17]),t(i,[2,18]),t(i,[2,19]),t(i,[2,20]),t(i,[2,21]),t(i,[2,22]),t(i,[2,23]),t(i,[2,24]),t(i,[2,25]),t(i,[2,26]),t(i,[2,27]),{32:[1,37]},{34:[1,38]},t(i,[2,30]),t(i,[2,31]),t(i,[2,32]),{39:[1,39]},t(i,[2,8]),t(i,[2,9]),t(i,[2,10]),t(i,[2,11]),t(i,[2,12]),t(i,[2,13]),t(i,[2,14]),t(i,[2,15]),t(i,[2,16]),{41:[1,40],43:[1,41]},t(i,[2,4]),t(i,[2,28]),t(i,[2,29]),t(i,[2,33]),t(i,[2,34],{42:[1,42],43:[1,43]}),t(i,[2,40],{41:[1,44]}),t(i,[2,35],{43:[1,45]}),t(i,[2,36]),t(i,[2,38],{42:[1,46]}),t(i,[2,37]),t(i,[2,39])],defaultActions:{},parseError:c(function(o,l){if(l.recoverable)this.trace(o);else{var d=new Error(o);throw d.hash=l,d}},"parseError"),parse:c(function(o){var l=this,d=[0],f=[],T=[null],r=[],V=this.table,e="",p=0,Y=0,F=2,A=1,$=r.slice.call(arguments,1),C=Object.create(this.lexer),Q={yy:{}};for(var rt in this.yy)Object.prototype.hasOwnProperty.call(this.yy,rt)&&(Q.yy[rt]=this.yy[rt]);C.setInput(o,Q.yy),Q.yy.lexer=C,Q.yy.parser=this,typeof C.yylloc>"u"&&(C.yylloc={});var ot=C.yylloc;r.push(ot);var ft=C.options&&C.options.ranges;typeof Q.yy.parseError=="function"?this.parseError=Q.yy.parseError:this.parseError=Object.getPrototypeOf(this).parseError;function ht(U){d.length=d.length-2*U,T.length=T.length-U,r.length=r.length-U}c(ht,"popStack");function ct(){var U;return U=f.pop()||C.lex()||A,typeof U!="number"&&(U instanceof Array&&(f=U,U=f.pop()),U=l.symbols_[U]||U),U}c(ct,"lex");for(var B,Z,q,nt,K={},it,J,Xt,gt;;){if(Z=d[d.length-1],this.defaultActions[Z]?q=this.defaultActions[Z]:((B===null||typeof B>"u")&&(B=ct()),q=V[Z]&&V[Z][B]),typeof q>"u"||!q.length||!q[0]){var Dt="";gt=[];for(it in V[Z])this.terminals_[it]&&it>F&&gt.push("'"+this.terminals_[it]+"'");C.showPosition?Dt="Parse error on line "+(p+1)+`:
`+C.showPosition()+`
Expecting `+gt.join(", ")+", got '"+(this.terminals_[B]||B)+"'":Dt="Parse error on line "+(p+1)+": Unexpected "+(B==A?"end of input":"'"+(this.terminals_[B]||B)+"'"),this.parseError(Dt,{text:C.match,token:this.terminals_[B]||B,line:C.yylineno,loc:ot,expected:gt})}if(q[0]instanceof Array&&q.length>1)throw new Error("Parse Error: multiple actions possible at state: "+Z+", token: "+B);switch(q[0]){case 1:d.push(B),T.push(C.yytext),r.push(C.yylloc),d.push(q[1]),B=null,Y=C.yyleng,e=C.yytext,p=C.yylineno,ot=C.yylloc;break;case 2:if(J=this.productions_[q[1]][1],K.$=T[T.length-J],K._$={first_line:r[r.length-(J||1)].first_line,last_line:r[r.length-1].last_line,first_column:r[r.length-(J||1)].first_column,last_column:r[r.length-1].last_column},ft&&(K._$.range=[r[r.length-(J||1)].range[0],r[r.length-1].range[1]]),nt=this.performAction.apply(K,[e,Y,p,Q.yy,q[1],T,r].concat($)),typeof nt<"u")return nt;J&&(d=d.slice(0,-1*J*2),T=T.slice(0,-1*J),r=r.slice(0,-1*J)),d.push(this.productions_[q[1]][0]),T.push(K.$),r.push(K._$),Xt=V[d[d.length-2]][d[d.length-1]],d.push(Xt);break;case 3:return!0}}return!0},"parse")},b=function(){var m={EOF:1,parseError:c(function(l,d){if(this.yy.parser)this.yy.parser.parseError(l,d);else throw new Error(l)},"parseError"),setInput:c(function(o,l){return this.yy=l||this.yy||{},this._input=o,this._more=this._backtrack=this.done=!1,this.yylineno=this.yyleng=0,this.yytext=this.matched=this.match="",this.conditionStack=["INITIAL"],this.yylloc={first_line:1,first_column:0,last_line:1,last_column:0},this.options.ranges&&(this.yylloc.range=[0,0]),this.offset=0,this},"setInput"),input:c(function(){var o=this._input[0];this.yytext+=o,this.yyleng++,this.offset++,this.match+=o,this.matched+=o;var l=o.match(/(?:\r\n?|\n).*/g);return l?(this.yylineno++,this.yylloc.last_line++):this.yylloc.last_column++,this.options.ranges&&this.yylloc.range[1]++,this._input=this._input.slice(1),o},"input"),unput:c(function(o){var l=o.length,d=o.split(/(?:\r\n?|\n)/g);this._input=o+this._input,this.yytext=this.yytext.substr(0,this.yytext.length-l),this.offset-=l;var f=this.match.split(/(?:\r\n?|\n)/g);this.match=this.match.substr(0,this.match.length-1),this.matched=this.matched.substr(0,this.matched.length-1),d.length-1&&(this.yylineno-=d.length-1);var T=this.yylloc.range;return this.yylloc={first_line:this.yylloc.first_line,last_line:this.yylineno+1,first_column:this.yylloc.first_column,last_column:d?(d.length===f.length?this.yylloc.first_column:0)+f[f.length-d.length].length-d[0].length:this.yylloc.first_column-l},this.options.ranges&&(this.yylloc.range=[T[0],T[0]+this.yyleng-l]),this.yyleng=this.yytext.length,this},"unput"),more:c(function(){return this._more=!0,this},"more"),reject:c(function(){if(this.options.backtrack_lexer)this._backtrack=!0;else return this.parseError("Lexical error on line "+(this.yylineno+1)+`. You can only invoke reject() in the lexer when the lexer is of the backtracking persuasion (options.backtrack_lexer = true).
`+this.showPosition(),{text:"",token:null,line:this.yylineno});return this},"reject"),less:c(function(o){this.unput(this.match.slice(o))},"less"),pastInput:c(function(){var o=this.matched.substr(0,this.matched.length-this.match.length);return(o.length>20?"...":"")+o.substr(-20).replace(/\n/g,"")},"pastInput"),upcomingInput:c(function(){var o=this.match;return o.length<20&&(o+=this._input.substr(0,20-o.length)),(o.substr(0,20)+(o.length>20?"...":"")).replace(/\n/g,"")},"upcomingInput"),showPosition:c(function(){var o=this.pastInput(),l=new Array(o.length+1).join("-");return o+this.upcomingInput()+`
`+l+"^"},"showPosition"),test_match:c(function(o,l){var d,f,T;if(this.options.backtrack_lexer&&(T={yylineno:this.yylineno,yylloc:{first_line:this.yylloc.first_line,last_line:this.last_line,first_column:this.yylloc.first_column,last_column:this.yylloc.last_column},yytext:this.yytext,match:this.match,matches:this.matches,matched:this.matched,yyleng:this.yyleng,offset:this.offset,_more:this._more,_input:this._input,yy:this.yy,conditionStack:this.conditionStack.slice(0),done:this.done},this.options.ranges&&(T.yylloc.range=this.yylloc.range.slice(0))),f=o[0].match(/(?:\r\n?|\n).*/g),f&&(this.yylineno+=f.length),this.yylloc={first_line:this.yylloc.last_line,last_line:this.yylineno+1,first_column:this.yylloc.last_column,last_column:f?f[f.length-1].length-f[f.length-1].match(/\r?\n?/)[0].length:this.yylloc.last_column+o[0].length},this.yytext+=o[0],this.match+=o[0],this.matches=o,this.yyleng=this.yytext.length,this.options.ranges&&(this.yylloc.range=[this.offset,this.offset+=this.yyleng]),this._more=!1,this._backtrack=!1,this._input=this._input.slice(o[0].length),this.matched+=o[0],d=this.performAction.call(this,this.yy,this,l,this.conditionStack[this.conditionStack.length-1]),this.done&&this._input&&(this.done=!1),d)return d;if(this._backtrack){for(var r in T)this[r]=T[r];return!1}return!1},"test_match"),next:c(function(){if(this.done)return this.EOF;this._input||(this.done=!0);var o,l,d,f;this._more||(this.yytext="",this.match="");for(var T=this._currentRules(),r=0;r<T.length;r++)if(d=this._input.match(this.rules[T[r]]),d&&(!l||d[0].length>l[0].length)){if(l=d,f=r,this.options.backtrack_lexer){if(o=this.test_match(d,T[r]),o!==!1)return o;if(this._backtrack){l=!1;continue}else return!1}else if(!this.options.flex)break}return l?(o=this.test_match(l,T[f]),o!==!1?o:!1):this._input===""?this.EOF:this.parseError("Lexical error on line "+(this.yylineno+1)+`. Unrecognized text.
`+this.showPosition(),{text:"",token:null,line:this.yylineno})},"next"),lex:c(function(){var l=this.next();return l||this.lex()},"lex"),begin:c(function(l){this.conditionStack.push(l)},"begin"),popState:c(function(){var l=this.conditionStack.length-1;return l>0?this.conditionStack.pop():this.conditionStack[0]},"popState"),_currentRules:c(function(){return this.conditionStack.length&&this.conditionStack[this.conditionStack.length-1]?this.conditions[this.conditionStack[this.conditionStack.length-1]].rules:this.conditions.INITIAL.rules},"_currentRules"),topState:c(function(l){return l=this.conditionStack.length-1-Math.abs(l||0),l>=0?this.conditionStack[l]:"INITIAL"},"topState"),pushState:c(function(l){this.begin(l)},"pushState"),stateStackSize:c(function(){return this.conditionStack.length},"stateStackSize"),options:{"case-insensitive":!0},performAction:c(function(l,d,f,T){switch(f){case 0:return this.begin("open_directive"),"open_directive";case 1:return this.begin("acc_title"),31;case 2:return this.popState(),"acc_title_value";case 3:return this.begin("acc_descr"),33;case 4:return this.popState(),"acc_descr_value";case 5:this.begin("acc_descr_multiline");break;case 6:this.popState();break;case 7:return"acc_descr_multiline_value";case 8:break;case 9:break;case 10:break;case 11:return 10;case 12:break;case 13:break;case 14:this.begin("href");break;case 15:this.popState();break;case 16:return 43;case 17:this.begin("callbackname");break;case 18:this.popState();break;case 19:this.popState(),this.begin("callbackargs");break;case 20:return 41;case 21:this.popState();break;case 22:return 42;case 23:this.begin("click");break;case 24:this.popState();break;case 25:return 40;case 26:return 4;case 27:return 22;case 28:return 23;case 29:return 24;case 30:return 25;case 31:return 26;case 32:return 28;case 33:return 27;case 34:return 29;case 35:return 12;case 36:return 13;case 37:return 14;case 38:return 15;case 39:return 16;case 40:return 17;case 41:return 18;case 42:return 20;case 43:return 21;case 44:return"date";case 45:return 30;case 46:return"accDescription";case 47:return 36;case 48:return 38;case 49:return 39;case 50:return":";case 51:return 6;case 52:return"INVALID"}},"anonymous"),rules:[/^(?:%%\{)/i,/^(?:accTitle\s*:\s*)/i,/^(?:(?!\n||)*[^\n]*)/i,/^(?:accDescr\s*:\s*)/i,/^(?:(?!\n||)*[^\n]*)/i,/^(?:accDescr\s*\{\s*)/i,/^(?:[\}])/i,/^(?:[^\}]*)/i,/^(?:%%(?!\{)*[^\n]*)/i,/^(?:[^\}]%%*[^\n]*)/i,/^(?:%%*[^\n]*[\n]*)/i,/^(?:[\n]+)/i,/^(?:\s+)/i,/^(?:%[^\n]*)/i,/^(?:href[\s]+["])/i,/^(?:["])/i,/^(?:[^"]*)/i,/^(?:call[\s]+)/i,/^(?:\([\s]*\))/i,/^(?:\()/i,/^(?:[^(]*)/i,/^(?:\))/i,/^(?:[^)]*)/i,/^(?:click[\s]+)/i,/^(?:[\s\n])/i,/^(?:[^\s\n]*)/i,/^(?:gantt\b)/i,/^(?:dateFormat\s[^#\n;]+)/i,/^(?:inclusiveEndDates\b)/i,/^(?:topAxis\b)/i,/^(?:axisFormat\s[^#\n;]+)/i,/^(?:tickInterval\s[^#\n;]+)/i,/^(?:includes\s[^#\n;]+)/i,/^(?:excludes\s[^#\n;]+)/i,/^(?:todayMarker\s[^\n;]+)/i,/^(?:weekday\s+monday\b)/i,/^(?:weekday\s+tuesday\b)/i,/^(?:weekday\s+wednesday\b)/i,/^(?:weekday\s+thursday\b)/i,/^(?:weekday\s+friday\b)/i,/^(?:weekday\s+saturday\b)/i,/^(?:weekday\s+sunday\b)/i,/^(?:weekend\s+friday\b)/i,/^(?:weekend\s+saturday\b)/i,/^(?:\d\d\d\d-\d\d-\d\d\b)/i,/^(?:title\s[^\n]+)/i,/^(?:accDescription\s[^#\n;]+)/i,/^(?:section\s[^\n]+)/i,/^(?:[^:\n]+)/i,/^(?::[^#\n;]+)/i,/^(?::)/i,/^(?:$)/i,/^(?:.)/i],conditions:{acc_descr_multiline:{rules:[6,7],inclusive:!1},acc_descr:{rules:[4],inclusive:!1},acc_title:{rules:[2],inclusive:!1},callbackargs:{rules:[21,22],inclusive:!1},callbackname:{rules:[18,19,20],inclusive:!1},href:{rules:[15,16],inclusive:!1},click:{rules:[24,25],inclusive:!1},INITIAL:{rules:[0,1,3,5,8,9,10,11,12,13,14,17,23,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52],inclusive:!0}}};return m}();x.lexer=b;function y(){this.yy={}}return c(y,"Parser"),y.prototype=x,x.Parser=y,new y}();Mt.parser=Mt;var Je=Mt;j.extend(qe);j.extend(Ze);j.extend(Ke);var te={friday:5,saturday:6},tt="",Wt="",Ot=void 0,Vt="",mt=[],kt=[],zt=new Map,Pt=[],wt=[],dt="",Nt="",oe=["active","done","crit","milestone","vert"],Rt=[],yt=!1,Bt=!1,Ht="sunday",_t="saturday",It=0,tr=c(function(){Pt=[],wt=[],dt="",Rt=[],xt=0,Ft=void 0,bt=void 0,H=[],tt="",Wt="",Nt="",Ot=void 0,Vt="",mt=[],kt=[],yt=!1,Bt=!1,It=0,zt=new Map,_e(),Ht="sunday",_t="saturday"},"clear"),er=c(function(t){Wt=t},"setAxisFormat"),rr=c(function(){return Wt},"getAxisFormat"),ir=c(function(t){Ot=t},"setTickInterval"),nr=c(function(){return Ot},"getTickInterval"),sr=c(function(t){Vt=t},"setTodayMarker"),ar=c(function(){return Vt},"getTodayMarker"),or=c(function(t){tt=t},"setDateFormat"),cr=c(function(){yt=!0},"enableInclusiveEndDates"),lr=c(function(){return yt},"endDatesAreInclusive"),ur=c(function(){Bt=!0},"enableTopAxis"),dr=c(function(){return Bt},"topAxisEnabled"),fr=c(function(t){Nt=t},"setDisplayMode"),hr=c(function(){return Nt},"getDisplayMode"),mr=c(function(){return tt},"getDateFormat"),kr=c(function(t){mt=t.toLowerCase().split(/[\s,]+/)},"setIncludes"),yr=c(function(){return mt},"getIncludes"),gr=c(function(t){kt=t.toLowerCase().split(/[\s,]+/)},"setExcludes"),pr=c(function(){return kt},"getExcludes"),vr=c(function(){return zt},"getLinks"),Tr=c(function(t){dt=t,Pt.push(t)},"addSection"),xr=c(function(){return Pt},"getSections"),br=c(function(){let t=ee();const i=10;let n=0;for(;!t&&n<i;)t=ee(),n++;return wt=H,wt},"getTasks"),ce=c(function(t,i,n,s){const a=t.format(i.trim()),h=t.format("YYYY-MM-DD");return s.includes(a)||s.includes(h)?!1:n.includes("weekends")&&(t.isoWeekday()===te[_t]||t.isoWeekday()===te[_t]+1)||n.includes(t.format("dddd").toLowerCase())?!0:n.includes(a)||n.includes(h)},"isInvalidDate"),wr=c(function(t){Ht=t},"setWeekday"),_r=c(function(){return Ht},"getWeekday"),Dr=c(function(t){_t=t},"setWeekend"),le=c(function(t,i,n,s){if(!n.length||t.manualEndTime)return;let a;t.startTime instanceof Date?a=j(t.startTime):a=j(t.startTime,i,!0),a=a.add(1,"d");let h;t.endTime instanceof Date?h=j(t.endTime):h=j(t.endTime,i,!0);const[u,v]=Sr(a,h,i,n,s);t.endTime=u.toDate(),t.renderEndTime=v},"checkTaskDates"),Sr=c(function(t,i,n,s,a){let h=!1,u=null;for(;t<=i;)h||(u=i.toDate()),h=ce(t,n,s,a),h&&(i=i.add(1,"d")),t=t.add(1,"d");return[i,u]},"fixTaskDates"),At=c(function(t,i,n){if(n=n.trim(),c(v=>{const D=v.trim();return D==="x"||D==="X"},"isTimestampFormat")(i)&&/^\d+$/.test(n))return new Date(Number(n));const h=/^after\s+(?<ids>[\d\w- ]+)/.exec(n);if(h!==null){let v=null;for(const E of h.groups.ids.split(" ")){let g=at(E);g!==void 0&&(!v||g.endTime>v.endTime)&&(v=g)}if(v)return v.endTime;const D=new Date;return D.setHours(0,0,0,0),D}let u=j(n,i.trim(),!0);if(u.isValid())return u.toDate();{st.debug("Invalid date:"+n),st.debug("With date format:"+i.trim());const v=new Date(n);if(v===void 0||isNaN(v.getTime())||v.getFullYear()<-1e4||v.getFullYear()>1e4)throw new Error("Invalid date:"+n);return v}},"getStartDate"),ue=c(function(t){const i=/^(\d+(?:\.\d+)?)([Mdhmswy]|ms)$/.exec(t.trim());return i!==null?[Number.parseFloat(i[1]),i[2]]:[NaN,"ms"]},"parseDuration"),de=c(function(t,i,n,s=!1){n=n.trim();const h=/^until\s+(?<ids>[\d\w- ]+)/.exec(n);if(h!==null){let g=null;for(const S of h.groups.ids.split(" ")){let w=at(S);w!==void 0&&(!g||w.startTime<g.startTime)&&(g=w)}if(g)return g.startTime;const L=new Date;return L.setHours(0,0,0,0),L}let u=j(n,i.trim(),!0);if(u.isValid())return s&&(u=u.add(1,"d")),u.toDate();let v=j(t);const[D,E]=ue(n);if(!Number.isNaN(D)){const g=v.add(D,E);g.isValid()&&(v=g)}return v.toDate()},"getEndDate"),xt=0,ut=c(function(t){return t===void 0?(xt=xt+1,"task"+xt):t},"parseId"),Cr=c(function(t,i){let n;i.substr(0,1)===":"?n=i.substr(1,i.length):n=i;const s=n.split(","),a={};Gt(s,a,oe);for(let u=0;u<s.length;u++)s[u]=s[u].trim();let h="";switch(s.length){case 1:a.id=ut(),a.startTime=t.endTime,h=s[0];break;case 2:a.id=ut(),a.startTime=At(void 0,tt,s[0]),h=s[1];break;case 3:a.id=ut(s[0]),a.startTime=At(void 0,tt,s[1]),h=s[2];break}return h&&(a.endTime=de(a.startTime,tt,h,yt),a.manualEndTime=j(h,"YYYY-MM-DD",!0).isValid(),le(a,tt,kt,mt)),a},"compileData"),Er=c(function(t,i){let n;i.substr(0,1)===":"?n=i.substr(1,i.length):n=i;const s=n.split(","),a={};Gt(s,a,oe);for(let h=0;h<s.length;h++)s[h]=s[h].trim();switch(s.length){case 1:a.id=ut(),a.startTime={type:"prevTaskEnd",id:t},a.endTime={data:s[0]};break;case 2:a.id=ut(),a.startTime={type:"getStartDate",startData:s[0]},a.endTime={data:s[1]};break;case 3:a.id=ut(s[0]),a.startTime={type:"getStartDate",startData:s[1]},a.endTime={data:s[2]};break}return a},"parseData"),Ft,bt,H=[],fe={},Mr=c(function(t,i){const n={section:dt,type:dt,processed:!1,manualEndTime:!1,renderEndTime:null,raw:{data:i},task:t,classes:[]},s=Er(bt,i);n.raw.startTime=s.startTime,n.raw.endTime=s.endTime,n.id=s.id,n.prevTaskId=bt,n.active=s.active,n.done=s.done,n.crit=s.crit,n.milestone=s.milestone,n.vert=s.vert,n.order=It,It++;const a=H.push(n);bt=n.id,fe[n.id]=a-1},"addTask"),at=c(function(t){const i=fe[t];return H[i]},"findTaskById"),Ir=c(function(t,i){const n={section:dt,type:dt,description:t,task:t,classes:[]},s=Cr(Ft,i);n.startTime=s.startTime,n.endTime=s.endTime,n.id=s.id,n.active=s.active,n.done=s.done,n.crit=s.crit,n.milestone=s.milestone,n.vert=s.vert,Ft=n,wt.push(n)},"addTaskOrg"),ee=c(function(){const t=c(function(n){const s=H[n];let a="";switch(H[n].raw.startTime.type){case"prevTaskEnd":{const h=at(s.prevTaskId);s.startTime=h.endTime;break}case"getStartDate":a=At(void 0,tt,H[n].raw.startTime.startData),a&&(H[n].startTime=a);break}return H[n].startTime&&(H[n].endTime=de(H[n].startTime,tt,H[n].raw.endTime.data,yt),H[n].endTime&&(H[n].processed=!0,H[n].manualEndTime=j(H[n].raw.endTime.data,"YYYY-MM-DD",!0).isValid(),le(H[n],tt,kt,mt))),H[n].processed},"compileTask");let i=!0;for(const[n,s]of H.entries())t(n),i=i&&s.processed;return i},"compileTasks"),Ar=c(function(t,i){let n=i;lt().securityLevel!=="loose"&&(n=we(i)),t.split(",").forEach(function(s){at(s)!==void 0&&(me(s,()=>{window.open(n,"_self")}),zt.set(s,n))}),he(t,"clickable")},"setLink"),he=c(function(t,i){t.split(",").forEach(function(n){let s=at(n);s!==void 0&&s.classes.push(i)})},"setClass"),Fr=c(function(t,i,n){if(lt().securityLevel!=="loose"||i===void 0)return;let s=[];if(typeof n=="string"){s=n.split(/,(?=(?:(?:[^"]*"){2})*[^"]*$)/);for(let h=0;h<s.length;h++){let u=s[h].trim();u.startsWith('"')&&u.endsWith('"')&&(u=u.substr(1,u.length-2)),s[h]=u}}s.length===0&&s.push(t),at(t)!==void 0&&me(t,()=>{De.runFunc(i,...s)})},"setClickFun"),me=c(function(t,i){Rt.push(function(){const n=document.querySelector(`[id="${t}"]`);n!==null&&n.addEventListener("click",function(){i()})},function(){const n=document.querySelector(`[id="${t}-text"]`);n!==null&&n.addEventListener("click",function(){i()})})},"pushFun"),Lr=c(function(t,i,n){t.split(",").forEach(function(s){Fr(s,i,n)}),he(t,"clickable")},"setClickEvent"),Yr=c(function(t){Rt.forEach(function(i){i(t)})},"bindFunctions"),Wr={getConfig:c(()=>lt().gantt,"getConfig"),clear:tr,setDateFormat:or,getDateFormat:mr,enableInclusiveEndDates:cr,endDatesAreInclusive:lr,enableTopAxis:ur,topAxisEnabled:dr,setAxisFormat:er,getAxisFormat:rr,setTickInterval:ir,getTickInterval:nr,setTodayMarker:sr,getTodayMarker:ar,setAccTitle:Te,getAccTitle:ve,setDiagramTitle:pe,getDiagramTitle:ge,setDisplayMode:fr,getDisplayMode:hr,setAccDescription:ye,getAccDescription:ke,addSection:Tr,getSections:xr,getTasks:br,addTask:Mr,findTaskById:at,addTaskOrg:Ir,setIncludes:kr,getIncludes:yr,setExcludes:gr,getExcludes:pr,setClickEvent:Lr,setLink:Ar,getLinks:vr,bindFunctions:Yr,parseDuration:ue,isInvalidDate:ce,setWeekday:wr,getWeekday:_r,setWeekend:Dr};function Gt(t,i,n){let s=!0;for(;s;)s=!1,n.forEach(function(a){const h="^\\s*"+a+"\\s*$",u=new RegExp(h);t[0].match(u)&&(i[a]=!0,t.shift(1),s=!0)})}c(Gt,"getTaskTags");j.extend(Se);var Or=c(function(){st.debug("Something is calling, setConf, remove the call")},"setConf"),re={monday:Ve,tuesday:Oe,wednesday:We,thursday:Ye,friday:Le,saturday:Fe,sunday:Ae},Vr=c((t,i)=>{let n=[...t].map(()=>-1/0),s=[...t].sort((h,u)=>h.startTime-u.startTime||h.order-u.order),a=0;for(const h of s)for(let u=0;u<n.length;u++)if(h.startTime>=n[u]){n[u]=h.endTime,h.order=u+i,u>a&&(a=u);break}return a},"getMaxIntersections"),et,Ct=1e4,zr=c(function(t,i,n,s){const a=lt().gantt,h=lt().securityLevel;let u;h==="sandbox"&&(u=pt("#i"+i));const v=h==="sandbox"?pt(u.nodes()[0].contentDocument.body):pt("body"),D=h==="sandbox"?u.nodes()[0].contentDocument:document,E=D.getElementById(i);et=E.parentElement.offsetWidth,et===void 0&&(et=1200),a.useWidth!==void 0&&(et=a.useWidth);const g=s.db.getTasks();let L=[];for(const k of g)L.push(k.type);L=R(L);const S={};let w=2*a.topPadding;if(s.db.getDisplayMode()==="compact"||a.displayMode==="compact"){const k={};for(const b of g)k[b.section]===void 0?k[b.section]=[b]:k[b.section].push(b);let x=0;for(const b of Object.keys(k)){const y=Vr(k[b],x)+1;x+=y,w+=y*(a.barHeight+a.barGap),S[b]=y}}else{w+=g.length*(a.barHeight+a.barGap);for(const k of L)S[k]=g.filter(x=>x.type===k).length}E.setAttribute("viewBox","0 0 "+et+" "+w);const G=v.select(`[id="${i}"]`),I=Ce().domain([Ee(g,function(k){return k.startTime}),Me(g,function(k){return k.endTime})]).rangeRound([0,et-a.leftPadding-a.rightPadding]);function _(k,x){const b=k.startTime,y=x.startTime;let m=0;return b>y?m=1:b<y&&(m=-1),m}c(_,"taskCompare"),g.sort(_),M(g,et,w),xe(G,w,et,a.useMaxWidth),G.append("text").text(s.db.getDiagramTitle()).attr("x",et/2).attr("y",a.titleTopMargin).attr("class","titleText");function M(k,x,b){const y=a.barHeight,m=y+a.barGap,o=a.topPadding,l=a.leftPadding,d=ze().domain([0,L.length]).range(["#00B9FA","#F95002"]).interpolate(Ie);O(m,o,l,x,b,k,s.db.getExcludes(),s.db.getIncludes()),N(l,o,x,b),W(k,m,o,l,y,d,x),X(m,o),z(l,o,x,b)}c(M,"makeGantt");function W(k,x,b,y,m,o,l){k.sort((e,p)=>e.vert===p.vert?0:e.vert?1:-1);const f=[...new Set(k.map(e=>e.order))].map(e=>k.find(p=>p.order===e));G.append("g").selectAll("rect").data(f).enter().append("rect").attr("x",0).attr("y",function(e,p){return p=e.order,p*x+b-2}).attr("width",function(){return l-a.rightPadding/2}).attr("height",x).attr("class",function(e){for(const[p,Y]of L.entries())if(e.type===Y)return"section section"+p%a.numberSectionStyles;return"section section0"}).enter();const T=G.append("g").selectAll("rect").data(k).enter(),r=s.db.getLinks();if(T.append("rect").attr("id",function(e){return e.id}).attr("rx",3).attr("ry",3).attr("x",function(e){return e.milestone?I(e.startTime)+y+.5*(I(e.endTime)-I(e.startTime))-.5*m:I(e.startTime)+y}).attr("y",function(e,p){return p=e.order,e.vert?a.gridLineStartPadding:p*x+b}).attr("width",function(e){return e.milestone?m:e.vert?.08*m:I(e.renderEndTime||e.endTime)-I(e.startTime)}).attr("height",function(e){return e.vert?g.length*(a.barHeight+a.barGap)+a.barHeight*2:m}).attr("transform-origin",function(e,p){return p=e.order,(I(e.startTime)+y+.5*(I(e.endTime)-I(e.startTime))).toString()+"px "+(p*x+b+.5*m).toString()+"px"}).attr("class",function(e){const p="task";let Y="";e.classes.length>0&&(Y=e.classes.join(" "));let F=0;for(const[$,C]of L.entries())e.type===C&&(F=$%a.numberSectionStyles);let A="";return e.active?e.crit?A+=" activeCrit":A=" active":e.done?e.crit?A=" doneCrit":A=" done":e.crit&&(A+=" crit"),A.length===0&&(A=" task"),e.milestone&&(A=" milestone "+A),e.vert&&(A=" vert "+A),A+=F,A+=" "+Y,p+A}),T.append("text").attr("id",function(e){return e.id+"-text"}).text(function(e){return e.task}).attr("font-size",a.fontSize).attr("x",function(e){let p=I(e.startTime),Y=I(e.renderEndTime||e.endTime);if(e.milestone&&(p+=.5*(I(e.endTime)-I(e.startTime))-.5*m,Y=p+m),e.vert)return I(e.startTime)+y;const F=this.getBBox().width;return F>Y-p?Y+F+1.5*a.leftPadding>l?p+y-5:Y+y+5:(Y-p)/2+p+y}).attr("y",function(e,p){return e.vert?a.gridLineStartPadding+g.length*(a.barHeight+a.barGap)+60:(p=e.order,p*x+a.barHeight/2+(a.fontSize/2-2)+b)}).attr("text-height",m).attr("class",function(e){const p=I(e.startTime);let Y=I(e.endTime);e.milestone&&(Y=p+m);const F=this.getBBox().width;let A="";e.classes.length>0&&(A=e.classes.join(" "));let $=0;for(const[Q,rt]of L.entries())e.type===rt&&($=Q%a.numberSectionStyles);let C="";return e.active&&(e.crit?C="activeCritText"+$:C="activeText"+$),e.done?e.crit?C=C+" doneCritText"+$:C=C+" doneText"+$:e.crit&&(C=C+" critText"+$),e.milestone&&(C+=" milestoneText"),e.vert&&(C+=" vertText"),F>Y-p?Y+F+1.5*a.leftPadding>l?A+" taskTextOutsideLeft taskTextOutside"+$+" "+C:A+" taskTextOutsideRight taskTextOutside"+$+" "+C+" width-"+F:A+" taskText taskText"+$+" "+C+" width-"+F}),lt().securityLevel==="sandbox"){let e;e=pt("#i"+i);const p=e.nodes()[0].contentDocument;T.filter(function(Y){return r.has(Y.id)}).each(function(Y){var F=p.querySelector("#"+Y.id),A=p.querySelector("#"+Y.id+"-text");const $=F.parentNode;var C=p.createElement("a");C.setAttribute("xlink:href",r.get(Y.id)),C.setAttribute("target","_top"),$.appendChild(C),C.appendChild(F),C.appendChild(A)})}}c(W,"drawRects");function O(k,x,b,y,m,o,l,d){if(l.length===0&&d.length===0)return;let f,T;for(const{startTime:F,endTime:A}of o)(f===void 0||F<f)&&(f=F),(T===void 0||A>T)&&(T=A);if(!f||!T)return;if(j(T).diff(j(f),"year")>5){st.warn("The difference between the min and max time is more than 5 years. This will cause performance issues. Skipping drawing exclude days.");return}const r=s.db.getDateFormat(),V=[];let e=null,p=j(f);for(;p.valueOf()<=T;)s.db.isInvalidDate(p,r,l,d)?e?e.end=p:e={start:p,end:p}:e&&(V.push(e),e=null),p=p.add(1,"d");G.append("g").selectAll("rect").data(V).enter().append("rect").attr("id",F=>"exclude-"+F.start.format("YYYY-MM-DD")).attr("x",F=>I(F.start.startOf("day"))+b).attr("y",a.gridLineStartPadding).attr("width",F=>I(F.end.endOf("day"))-I(F.start.startOf("day"))).attr("height",m-x-a.gridLineStartPadding).attr("transform-origin",function(F,A){return(I(F.start)+b+.5*(I(F.end)-I(F.start))).toString()+"px "+(A*k+.5*m).toString()+"px"}).attr("class","exclude-range")}c(O,"drawExcludeDays");function P(k,x,b,y){if(b<=0||k>x)return 1/0;const m=x-k,o=j.duration({[y??"day"]:b}).asMilliseconds();return o<=0?1/0:Math.ceil(m/o)}c(P,"getEstimatedTickCount");function N(k,x,b,y){const m=s.db.getDateFormat(),o=s.db.getAxisFormat();let l;o?l=o:m==="D"?l="%d":l=a.axisFormat??"%Y-%m-%d";let d=$e(I).tickSize(-y+x+a.gridLineStartPadding).tickFormat($t(l));const T=/^([1-9]\d*)(millisecond|second|minute|hour|day|week|month)$/.exec(s.db.getTickInterval()||a.tickInterval);if(T!==null){const r=parseInt(T[1],10);if(isNaN(r)||r<=0)st.warn(`Invalid tick interval value: "${T[1]}". Skipping custom tick interval.`);else{const V=T[2],e=s.db.getWeekday()||a.weekday,p=I.domain(),Y=p[0],F=p[1],A=P(Y,F,r,V);if(A>Ct)st.warn(`The tick interval "${r}${V}" would generate ${A} ticks, which exceeds the maximum allowed (${Ct}). This may indicate an invalid date or time range. Skipping custom tick interval.`);else switch(V){case"millisecond":d.ticks(Kt.every(r));break;case"second":d.ticks(Qt.every(r));break;case"minute":d.ticks(Zt.every(r));break;case"hour":d.ticks(Ut.every(r));break;case"day":d.ticks(qt.every(r));break;case"week":d.ticks(re[e].every(r));break;case"month":d.ticks(jt.every(r));break}}}if(G.append("g").attr("class","grid").attr("transform","translate("+k+", "+(y-50)+")").call(d).selectAll("text").style("text-anchor","middle").attr("fill","#000").attr("stroke","none").attr("font-size",10).attr("dy","1em"),s.db.topAxisEnabled()||a.topAxis){let r=Xe(I).tickSize(-y+x+a.gridLineStartPadding).tickFormat($t(l));if(T!==null){const V=parseInt(T[1],10);if(isNaN(V)||V<=0)st.warn(`Invalid tick interval value: "${T[1]}". Skipping custom tick interval.`);else{const e=T[2],p=s.db.getWeekday()||a.weekday,Y=I.domain(),F=Y[0],A=Y[1];if(P(F,A,V,e)<=Ct)switch(e){case"millisecond":r.ticks(Kt.every(V));break;case"second":r.ticks(Qt.every(V));break;case"minute":r.ticks(Zt.every(V));break;case"hour":r.ticks(Ut.every(V));break;case"day":r.ticks(qt.every(V));break;case"week":r.ticks(re[p].every(V));break;case"month":r.ticks(jt.every(V));break}}}G.append("g").attr("class","grid").attr("transform","translate("+k+", "+x+")").call(r).selectAll("text").style("text-anchor","middle").attr("fill","#000").attr("stroke","none").attr("font-size",10)}}c(N,"makeGrid");function X(k,x){let b=0;const y=Object.keys(S).map(m=>[m,S[m]]);G.append("g").selectAll("text").data(y).enter().append(function(m){const o=m[0].split(be.lineBreakRegex),l=-(o.length-1)/2,d=D.createElementNS("http://www.w3.org/2000/svg","text");d.setAttribute("dy",l+"em");for(const[f,T]of o.entries()){const r=D.createElementNS("http://www.w3.org/2000/svg","tspan");r.setAttribute("alignment-baseline","central"),r.setAttribute("x","10"),f>0&&r.setAttribute("dy","1em"),r.textContent=T,d.appendChild(r)}return d}).attr("x",10).attr("y",function(m,o){if(o>0)for(let l=0;l<o;l++)return b+=y[o-1][1],m[1]*k/2+b*k+x;else return m[1]*k/2+x}).attr("font-size",a.sectionFontSize).attr("class",function(m){for(const[o,l]of L.entries())if(m[0]===l)return"sectionTitle sectionTitle"+o%a.numberSectionStyles;return"sectionTitle"})}c(X,"vertLabels");function z(k,x,b,y){const m=s.db.getTodayMarker();if(m==="off")return;const o=G.append("g").attr("class","today"),l=new Date,d=o.append("line");d.attr("x1",I(l)+k).attr("x2",I(l)+k).attr("y1",a.titleTopMargin).attr("y2",y-a.titleTopMargin).attr("class","today"),m!==""&&d.attr("style",m.replace(/,/g,";"))}c(z,"drawToday");function R(k){const x={},b=[];for(let y=0,m=k.length;y<m;++y)Object.prototype.hasOwnProperty.call(x,k[y])||(x[k[y]]=!0,b.push(k[y]));return b}c(R,"checkUnique")},"draw"),Pr={setConf:Or,draw:zr},Nr=c(t=>`
  .mermaid-main-font {
        font-family: ${t.fontFamily};
  }

  .exclude-range {
    fill: ${t.excludeBkgColor};
  }

  .section {
    stroke: none;
    opacity: 0.2;
  }

  .section0 {
    fill: ${t.sectionBkgColor};
  }

  .section2 {
    fill: ${t.sectionBkgColor2};
  }

  .section1,
  .section3 {
    fill: ${t.altSectionBkgColor};
    opacity: 0.2;
  }

  .sectionTitle0 {
    fill: ${t.titleColor};
  }

  .sectionTitle1 {
    fill: ${t.titleColor};
  }

  .sectionTitle2 {
    fill: ${t.titleColor};
  }

  .sectionTitle3 {
    fill: ${t.titleColor};
  }

  .sectionTitle {
    text-anchor: start;
    font-family: ${t.fontFamily};
  }


  /* Grid and axis */

  .grid .tick {
    stroke: ${t.gridColor};
    opacity: 0.8;
    shape-rendering: crispEdges;
  }

  .grid .tick text {
    font-family: ${t.fontFamily};
    fill: ${t.textColor};
  }

  .grid path {
    stroke-width: 0;
  }


  /* Today line */

  .today {
    fill: none;
    stroke: ${t.todayLineColor};
    stroke-width: 2px;
  }


  /* Task styling */

  /* Default task */

  .task {
    stroke-width: 2;
  }

  .taskText {
    text-anchor: middle;
    font-family: ${t.fontFamily};
  }

  .taskTextOutsideRight {
    fill: ${t.taskTextDarkColor};
    text-anchor: start;
    font-family: ${t.fontFamily};
  }

  .taskTextOutsideLeft {
    fill: ${t.taskTextDarkColor};
    text-anchor: end;
  }


  /* Special case clickable */

  .task.clickable {
    cursor: pointer;
  }

  .taskText.clickable {
    cursor: pointer;
    fill: ${t.taskTextClickableColor} !important;
    font-weight: bold;
  }

  .taskTextOutsideLeft.clickable {
    cursor: pointer;
    fill: ${t.taskTextClickableColor} !important;
    font-weight: bold;
  }

  .taskTextOutsideRight.clickable {
    cursor: pointer;
    fill: ${t.taskTextClickableColor} !important;
    font-weight: bold;
  }


  /* Specific task settings for the sections*/

  .taskText0,
  .taskText1,
  .taskText2,
  .taskText3 {
    fill: ${t.taskTextColor};
  }

  .task0,
  .task1,
  .task2,
  .task3 {
    fill: ${t.taskBkgColor};
    stroke: ${t.taskBorderColor};
  }

  .taskTextOutside0,
  .taskTextOutside2
  {
    fill: ${t.taskTextOutsideColor};
  }

  .taskTextOutside1,
  .taskTextOutside3 {
    fill: ${t.taskTextOutsideColor};
  }


  /* Active task */

  .active0,
  .active1,
  .active2,
  .active3 {
    fill: ${t.activeTaskBkgColor};
    stroke: ${t.activeTaskBorderColor};
  }

  .activeText0,
  .activeText1,
  .activeText2,
  .activeText3 {
    fill: ${t.taskTextDarkColor} !important;
  }


  /* Completed task */

  .done0,
  .done1,
  .done2,
  .done3 {
    stroke: ${t.doneTaskBorderColor};
    fill: ${t.doneTaskBkgColor};
    stroke-width: 2;
  }

  .doneText0,
  .doneText1,
  .doneText2,
  .doneText3 {
    fill: ${t.taskTextDarkColor} !important;
  }


  /* Tasks on the critical line */

  .crit0,
  .crit1,
  .crit2,
  .crit3 {
    stroke: ${t.critBorderColor};
    fill: ${t.critBkgColor};
    stroke-width: 2;
  }

  .activeCrit0,
  .activeCrit1,
  .activeCrit2,
  .activeCrit3 {
    stroke: ${t.critBorderColor};
    fill: ${t.activeTaskBkgColor};
    stroke-width: 2;
  }

  .doneCrit0,
  .doneCrit1,
  .doneCrit2,
  .doneCrit3 {
    stroke: ${t.critBorderColor};
    fill: ${t.doneTaskBkgColor};
    stroke-width: 2;
    cursor: pointer;
    shape-rendering: crispEdges;
  }

  .milestone {
    transform: rotate(45deg) scale(0.8,0.8);
  }

  .milestoneText {
    font-style: italic;
  }
  .doneCritText0,
  .doneCritText1,
  .doneCritText2,
  .doneCritText3 {
    fill: ${t.taskTextDarkColor} !important;
  }

  .vert {
    stroke: ${t.vertLineColor};
  }

  .vertText {
    font-size: 15px;
    text-anchor: middle;
    fill: ${t.vertLineColor} !important;
  }

  .activeCritText0,
  .activeCritText1,
  .activeCritText2,
  .activeCritText3 {
    fill: ${t.taskTextDarkColor} !important;
  }

  .titleText {
    text-anchor: middle;
    font-size: 18px;
    fill: ${t.titleColor||t.textColor};
    font-family: ${t.fontFamily};
  }
`,"getStyles"),Rr=Nr,qr={parser:Je,db:Wr,renderer:Pr,styles:Rr};export{qr as diagram};
//# sourceMappingURL=IN-wCUeb.js.map
