/*!
 * ONNX Runtime Web v1.21.0-dev.20250206-d981b153d3
 * Copyright (c) Microsoft Corporation. All rights reserved.
 * Licensed under the MIT License.
 */
var Rn=Object.defineProperty;var Vp=Object.getOwnPropertyDescriptor;var Wp=Object.getOwnPropertyNames;var Lp=Object.prototype.hasOwnProperty;var Un=(e=>typeof require<"u"?require:typeof Proxy<"u"?new Proxy(e,{get:(t,r)=>(typeof require<"u"?require:t)[r]}):e)(function(e){if(typeof require<"u")return require.apply(this,arguments);throw Error('Dynamic require of "'+e+'" is not supported')});var U=(e,t)=>()=>(e&&(t=e(e=0)),t);var Ht=(e,t)=>{for(var r in t)Rn(e,r,{get:t[r],enumerable:!0})},Gp=(e,t,r,n)=>{if(t&&typeof t=="object"||typeof t=="function")for(let o of Wp(t))!Lp.call(e,o)&&o!==r&&Rn(e,o,{get:()=>t[o],enumerable:!(n=Vp(t,o))||n.enumerable});return e};var gr=e=>Gp(Rn({},"__esModule",{value:!0}),e);var br,St,Tt,Hp,Xi,Nn=U(()=>{"use strict";br=new Map,St=[],Tt=(e,t,r)=>{if(t&&typeof t.init=="function"&&typeof t.createInferenceSessionHandler=="function"){let n=br.get(e);if(n===void 0)br.set(e,{backend:t,priority:r});else{if(n.priority>r)return;if(n.priority===r&&n.backend!==t)throw new Error(`cannot register backend "${e}" using priority ${r}`)}if(r>=0){let o=St.indexOf(e);o!==-1&&St.splice(o,1);for(let i=0;i<St.length;i++)if(br.get(St[i]).priority<=r){St.splice(i,0,e);return}St.push(e)}return}throw new TypeError("not a valid backend")},Hp=async e=>{let t=br.get(e);if(!t)return"backend not found.";if(t.initialized)return t.backend;if(t.aborted)return t.error;{let r=!!t.initPromise;try{return r||(t.initPromise=t.backend.init(e)),await t.initPromise,t.initialized=!0,t.backend}catch(n){return r||(t.error=`${n}`,t.aborted=!0),t.error}finally{delete t.initPromise}}},Xi=async e=>{let t=e.executionProviders||[],r=t.map(l=>typeof l=="string"?l:l.name),n=r.length===0?St:r,o,i=[],a=new Set;for(let l of n){let p=await Hp(l);typeof p=="string"?i.push({name:l,err:p}):(o||(o=p),o===p&&a.add(l))}if(!o)throw new Error(`no available backend found. ERR: ${i.map(l=>`[${l.name}] ${l.err}`).join(", ")}`);for(let{name:l,err:p}of i)r.includes(l)&&console.warn(`removing requested execution provider "${l}" from session options because it is not available: ${p}`);let d=t.filter(l=>a.has(typeof l=="string"?l:l.name));return[o,new Proxy(e,{get:(l,p)=>p==="executionProviders"?d:Reflect.get(l,p)})]}});var Ji=U(()=>{"use strict";Nn()});var ea,ta=U(()=>{"use strict";ea="1.21.0-dev.20250206-d981b153d3"});var ra,Ue,Vn=U(()=>{"use strict";ta();ra="warning",Ue={wasm:{},webgl:{},webgpu:{},versions:{common:ea},set logLevel(e){if(e!==void 0){if(typeof e!="string"||["verbose","info","warning","error","fatal"].indexOf(e)===-1)throw new Error(`Unsupported logging level: ${e}`);ra=e}},get logLevel(){return ra}};Object.defineProperty(Ue,"logLevel",{enumerable:!0})});var _e,na=U(()=>{"use strict";Vn();_e=Ue});var oa,ia,aa=U(()=>{"use strict";oa=(e,t)=>{let r=typeof document<"u"?document.createElement("canvas"):new OffscreenCanvas(1,1);r.width=e.dims[3],r.height=e.dims[2];let n=r.getContext("2d");if(n!=null){let o,i;t?.tensorLayout!==void 0&&t.tensorLayout==="NHWC"?(o=e.dims[2],i=e.dims[3]):(o=e.dims[3],i=e.dims[2]);let a=t?.format!==void 0?t.format:"RGB",d=t?.norm,l,p;d===void 0||d.mean===void 0?l=[255,255,255,255]:typeof d.mean=="number"?l=[d.mean,d.mean,d.mean,d.mean]:(l=[d.mean[0],d.mean[1],d.mean[2],0],d.mean[3]!==void 0&&(l[3]=d.mean[3])),d===void 0||d.bias===void 0?p=[0,0,0,0]:typeof d.bias=="number"?p=[d.bias,d.bias,d.bias,d.bias]:(p=[d.bias[0],d.bias[1],d.bias[2],0],d.bias[3]!==void 0&&(p[3]=d.bias[3]));let m=i*o,u=0,h=m,_=m*2,y=-1;a==="RGBA"?(u=0,h=m,_=m*2,y=m*3):a==="RGB"?(u=0,h=m,_=m*2):a==="RBG"&&(u=0,_=m,h=m*2);for(let g=0;g<i;g++)for(let x=0;x<o;x++){let $=(e.data[u++]-p[0])*l[0],v=(e.data[h++]-p[1])*l[1],S=(e.data[_++]-p[2])*l[2],T=y===-1?255:(e.data[y++]-p[3])*l[3];n.fillStyle="rgba("+$+","+v+","+S+","+T+")",n.fillRect(x,g,1,1)}if("toDataURL"in r)return r.toDataURL();throw new Error("toDataURL is not supported")}else throw new Error("Can not access image data")},ia=(e,t)=>{let r=typeof document<"u"?document.createElement("canvas").getContext("2d"):new OffscreenCanvas(1,1).getContext("2d"),n;if(r!=null){let o,i,a;t?.tensorLayout!==void 0&&t.tensorLayout==="NHWC"?(o=e.dims[2],i=e.dims[1],a=e.dims[3]):(o=e.dims[3],i=e.dims[2],a=e.dims[1]);let d=t!==void 0&&t.format!==void 0?t.format:"RGB",l=t?.norm,p,m;l===void 0||l.mean===void 0?p=[255,255,255,255]:typeof l.mean=="number"?p=[l.mean,l.mean,l.mean,l.mean]:(p=[l.mean[0],l.mean[1],l.mean[2],255],l.mean[3]!==void 0&&(p[3]=l.mean[3])),l===void 0||l.bias===void 0?m=[0,0,0,0]:typeof l.bias=="number"?m=[l.bias,l.bias,l.bias,l.bias]:(m=[l.bias[0],l.bias[1],l.bias[2],0],l.bias[3]!==void 0&&(m[3]=l.bias[3]));let u=i*o;if(t!==void 0&&(t.format!==void 0&&a===4&&t.format!=="RGBA"||a===3&&t.format!=="RGB"&&t.format!=="BGR"))throw new Error("Tensor format doesn't match input tensor dims");let h=4,_=0,y=1,g=2,x=3,$=0,v=u,S=u*2,T=-1;d==="RGBA"?($=0,v=u,S=u*2,T=u*3):d==="RGB"?($=0,v=u,S=u*2):d==="RBG"&&($=0,S=u,v=u*2),n=r.createImageData(o,i);for(let A=0;A<i*o;_+=h,y+=h,g+=h,x+=h,A++)n.data[_]=(e.data[$++]-m[0])*p[0],n.data[y]=(e.data[v++]-m[1])*p[1],n.data[g]=(e.data[S++]-m[2])*p[2],n.data[x]=T===-1?255:(e.data[T++]-m[3])*p[3]}else throw new Error("Can not access image data");return n}});var Wn,sa,ua,da,la,ca,pa=U(()=>{"use strict";yr();Wn=(e,t)=>{if(e===void 0)throw new Error("Image buffer must be defined");if(t.height===void 0||t.width===void 0)throw new Error("Image height and width must be defined");if(t.tensorLayout==="NHWC")throw new Error("NHWC Tensor layout is not supported yet");let{height:r,width:n}=t,o=t.norm??{mean:255,bias:0},i,a;typeof o.mean=="number"?i=[o.mean,o.mean,o.mean,o.mean]:i=[o.mean[0],o.mean[1],o.mean[2],o.mean[3]??255],typeof o.bias=="number"?a=[o.bias,o.bias,o.bias,o.bias]:a=[o.bias[0],o.bias[1],o.bias[2],o.bias[3]??0];let d=t.format!==void 0?t.format:"RGBA",l=t.tensorFormat!==void 0&&t.tensorFormat!==void 0?t.tensorFormat:"RGB",p=r*n,m=l==="RGBA"?new Float32Array(p*4):new Float32Array(p*3),u=4,h=0,_=1,y=2,g=3,x=0,$=p,v=p*2,S=-1;d==="RGB"&&(u=3,h=0,_=1,y=2,g=-1),l==="RGBA"?S=p*3:l==="RBG"?(x=0,v=p,$=p*2):l==="BGR"&&(v=0,$=p,x=p*2);for(let A=0;A<p;A++,h+=u,y+=u,_+=u,g+=u)m[x++]=(e[h]+a[0])/i[0],m[$++]=(e[_]+a[1])/i[1],m[v++]=(e[y]+a[2])/i[2],S!==-1&&g!==-1&&(m[S++]=(e[g]+a[3])/i[3]);return l==="RGBA"?new ze("float32",m,[1,4,r,n]):new ze("float32",m,[1,3,r,n])},sa=async(e,t)=>{let r=typeof HTMLImageElement<"u"&&e instanceof HTMLImageElement,n=typeof ImageData<"u"&&e instanceof ImageData,o=typeof ImageBitmap<"u"&&e instanceof ImageBitmap,i=typeof e=="string",a,d=t??{},l=()=>{if(typeof document<"u")return document.createElement("canvas");if(typeof OffscreenCanvas<"u")return new OffscreenCanvas(1,1);throw new Error("Canvas is not supported")},p=m=>typeof HTMLCanvasElement<"u"&&m instanceof HTMLCanvasElement||m instanceof OffscreenCanvas?m.getContext("2d"):null;if(r){let m=l();m.width=e.width,m.height=e.height;let u=p(m);if(u!=null){let h=e.height,_=e.width;if(t!==void 0&&t.resizedHeight!==void 0&&t.resizedWidth!==void 0&&(h=t.resizedHeight,_=t.resizedWidth),t!==void 0){if(d=t,t.tensorFormat!==void 0)throw new Error("Image input config format must be RGBA for HTMLImageElement");d.tensorFormat="RGBA",d.height=h,d.width=_}else d.tensorFormat="RGBA",d.height=h,d.width=_;u.drawImage(e,0,0),a=u.getImageData(0,0,_,h).data}else throw new Error("Can not access image data")}else if(n){let m,u;if(t!==void 0&&t.resizedWidth!==void 0&&t.resizedHeight!==void 0?(m=t.resizedHeight,u=t.resizedWidth):(m=e.height,u=e.width),t!==void 0&&(d=t),d.format="RGBA",d.height=m,d.width=u,t!==void 0){let h=l();h.width=u,h.height=m;let _=p(h);if(_!=null)_.putImageData(e,0,0),a=_.getImageData(0,0,u,m).data;else throw new Error("Can not access image data")}else a=e.data}else if(o){if(t===void 0)throw new Error("Please provide image config with format for Imagebitmap");let m=l();m.width=e.width,m.height=e.height;let u=p(m);if(u!=null){let h=e.height,_=e.width;return u.drawImage(e,0,0,_,h),a=u.getImageData(0,0,_,h).data,d.height=h,d.width=_,Wn(a,d)}else throw new Error("Can not access image data")}else{if(i)return new Promise((m,u)=>{let h=l(),_=p(h);if(!e||!_)return u();let y=new Image;y.crossOrigin="Anonymous",y.src=e,y.onload=()=>{h.width=y.width,h.height=y.height,_.drawImage(y,0,0,h.width,h.height);let g=_.getImageData(0,0,h.width,h.height);d.height=h.height,d.width=h.width,m(Wn(g.data,d))}});throw new Error("Input data provided is not supported - aborted tensor creation")}if(a!==void 0)return Wn(a,d);throw new Error("Input data provided is not supported - aborted tensor creation")},ua=(e,t)=>{let{width:r,height:n,download:o,dispose:i}=t,a=[1,n,r,4];return new ze({location:"texture",type:"float32",texture:e,dims:a,download:o,dispose:i})},da=(e,t)=>{let{dataType:r,dims:n,download:o,dispose:i}=t;return new ze({location:"gpu-buffer",type:r??"float32",gpuBuffer:e,dims:n,download:o,dispose:i})},la=(e,t)=>{let{dataType:r,dims:n,download:o,dispose:i}=t;return new ze({location:"ml-tensor",type:r??"float32",mlTensor:e,dims:n,download:o,dispose:i})},ca=(e,t,r)=>new ze({location:"cpu-pinned",type:e,data:t,dims:r??[t.length]})});var It,Ft,ma,fa,ha=U(()=>{"use strict";It=new Map([["float32",Float32Array],["uint8",Uint8Array],["int8",Int8Array],["uint16",Uint16Array],["int16",Int16Array],["int32",Int32Array],["bool",Uint8Array],["float64",Float64Array],["uint32",Uint32Array],["int4",Uint8Array],["uint4",Uint8Array]]),Ft=new Map([[Float32Array,"float32"],[Uint8Array,"uint8"],[Int8Array,"int8"],[Uint16Array,"uint16"],[Int16Array,"int16"],[Int32Array,"int32"],[Float64Array,"float64"],[Uint32Array,"uint32"]]),ma=!1,fa=()=>{if(!ma){ma=!0;let e=typeof BigInt64Array<"u"&&BigInt64Array.from,t=typeof BigUint64Array<"u"&&BigUint64Array.from,r=typeof Float16Array<"u"&&Float16Array.from;e&&(It.set("int64",BigInt64Array),Ft.set(BigInt64Array,"int64")),t&&(It.set("uint64",BigUint64Array),Ft.set(BigUint64Array,"uint64")),r?(It.set("float16",Float16Array),Ft.set(Float16Array,"float16")):It.set("float16",Uint16Array)}}});var ga,ba,ya=U(()=>{"use strict";yr();ga=e=>{let t=1;for(let r=0;r<e.length;r++){let n=e[r];if(typeof n!="number"||!Number.isSafeInteger(n))throw new TypeError(`dims[${r}] must be an integer, got: ${n}`);if(n<0)throw new RangeError(`dims[${r}] must be a non-negative integer, got: ${n}`);t*=n}return t},ba=(e,t)=>{switch(e.location){case"cpu":return new ze(e.type,e.data,t);case"cpu-pinned":return new ze({location:"cpu-pinned",data:e.data,type:e.type,dims:t});case"texture":return new ze({location:"texture",texture:e.texture,type:e.type,dims:t});case"gpu-buffer":return new ze({location:"gpu-buffer",gpuBuffer:e.gpuBuffer,type:e.type,dims:t});case"ml-tensor":return new ze({location:"ml-tensor",mlTensor:e.mlTensor,type:e.type,dims:t});default:throw new Error(`tensorReshape: tensor location ${e.location} is not supported`)}}});var ze,yr=U(()=>{"use strict";aa();pa();ha();ya();ze=class{constructor(t,r,n){fa();let o,i;if(typeof t=="object"&&"location"in t)switch(this.dataLocation=t.location,o=t.type,i=t.dims,t.location){case"cpu-pinned":{let d=It.get(o);if(!d)throw new TypeError(`unsupported type "${o}" to create tensor from pinned buffer`);if(!(t.data instanceof d))throw new TypeError(`buffer should be of type ${d.name}`);this.cpuData=t.data;break}case"texture":{if(o!=="float32")throw new TypeError(`unsupported type "${o}" to create tensor from texture`);this.gpuTextureData=t.texture,this.downloader=t.download,this.disposer=t.dispose;break}case"gpu-buffer":{if(o!=="float32"&&o!=="float16"&&o!=="int32"&&o!=="int64"&&o!=="uint32"&&o!=="uint8"&&o!=="bool"&&o!=="uint4"&&o!=="int4")throw new TypeError(`unsupported type "${o}" to create tensor from gpu buffer`);this.gpuBufferData=t.gpuBuffer,this.downloader=t.download,this.disposer=t.dispose;break}case"ml-tensor":{if(o!=="float32"&&o!=="float16"&&o!=="int32"&&o!=="int64"&&o!=="uint32"&&o!=="uint64"&&o!=="int8"&&o!=="uint8"&&o!=="bool"&&o!=="uint4"&&o!=="int4")throw new TypeError(`unsupported type "${o}" to create tensor from MLTensor`);this.mlTensorData=t.mlTensor,this.downloader=t.download,this.disposer=t.dispose;break}default:throw new Error(`Tensor constructor: unsupported location '${this.dataLocation}'`)}else{let d,l;if(typeof t=="string")if(o=t,l=n,t==="string"){if(!Array.isArray(r))throw new TypeError("A string tensor's data must be a string array.");d=r}else{let p=It.get(t);if(p===void 0)throw new TypeError(`Unsupported tensor type: ${t}.`);if(Array.isArray(r)){if(t==="float16"&&p===Uint16Array||t==="uint4"||t==="int4")throw new TypeError(`Creating a ${t} tensor from number array is not supported. Please use ${p.name} as data.`);t==="uint64"||t==="int64"?d=p.from(r,BigInt):d=p.from(r)}else if(r instanceof p)d=r;else if(r instanceof Uint8ClampedArray)if(t==="uint8")d=Uint8Array.from(r);else throw new TypeError("A Uint8ClampedArray tensor's data must be type of uint8");else throw new TypeError(`A ${o} tensor's data must be type of ${p}`)}else if(l=r,Array.isArray(t)){if(t.length===0)throw new TypeError("Tensor type cannot be inferred from an empty array.");let p=typeof t[0];if(p==="string")o="string",d=t;else if(p==="boolean")o="bool",d=Uint8Array.from(t);else throw new TypeError(`Invalid element type of data array: ${p}.`)}else if(t instanceof Uint8ClampedArray)o="uint8",d=Uint8Array.from(t);else{let p=Ft.get(t.constructor);if(p===void 0)throw new TypeError(`Unsupported type for tensor data: ${t.constructor}.`);o=p,d=t}if(l===void 0)l=[d.length];else if(!Array.isArray(l))throw new TypeError("A tensor's dims must be a number array");i=l,this.cpuData=d,this.dataLocation="cpu"}let a=ga(i);if(this.cpuData&&a!==this.cpuData.length&&!((o==="uint4"||o==="int4")&&Math.ceil(a/2)===this.cpuData.length))throw new Error(`Tensor's size(${a}) does not match data length(${this.cpuData.length}).`);this.type=o,this.dims=i,this.size=a}static async fromImage(t,r){return sa(t,r)}static fromTexture(t,r){return ua(t,r)}static fromGpuBuffer(t,r){return da(t,r)}static fromMLTensor(t,r){return la(t,r)}static fromPinnedBuffer(t,r,n){return ca(t,r,n)}toDataURL(t){return oa(this,t)}toImageData(t){return ia(this,t)}get data(){if(this.ensureValid(),!this.cpuData)throw new Error("The data is not on CPU. Use `getData()` to download GPU data to CPU, or use `texture` or `gpuBuffer` property to access the GPU data directly.");return this.cpuData}get location(){return this.dataLocation}get texture(){if(this.ensureValid(),!this.gpuTextureData)throw new Error("The data is not stored as a WebGL texture.");return this.gpuTextureData}get gpuBuffer(){if(this.ensureValid(),!this.gpuBufferData)throw new Error("The data is not stored as a WebGPU buffer.");return this.gpuBufferData}get mlTensor(){if(this.ensureValid(),!this.mlTensorData)throw new Error("The data is not stored as a WebNN MLTensor.");return this.mlTensorData}async getData(t){switch(this.ensureValid(),this.dataLocation){case"cpu":case"cpu-pinned":return this.data;case"texture":case"gpu-buffer":case"ml-tensor":{if(!this.downloader)throw new Error("The current tensor is not created with a specified data downloader.");if(this.isDownloading)throw new Error("The current tensor is being downloaded.");try{this.isDownloading=!0;let r=await this.downloader();return this.downloader=void 0,this.dataLocation="cpu",this.cpuData=r,t&&this.disposer&&(this.disposer(),this.disposer=void 0),r}finally{this.isDownloading=!1}}default:throw new Error(`cannot get data from location: ${this.dataLocation}`)}}dispose(){if(this.isDownloading)throw new Error("The current tensor is being downloaded.");this.disposer&&(this.disposer(),this.disposer=void 0),this.cpuData=void 0,this.gpuTextureData=void 0,this.gpuBufferData=void 0,this.mlTensorData=void 0,this.downloader=void 0,this.isDownloading=void 0,this.dataLocation="none"}ensureValid(){if(this.dataLocation==="none")throw new Error("The tensor is disposed.")}reshape(t){if(this.ensureValid(),this.downloader||this.disposer)throw new Error("Cannot reshape a tensor that owns GPU resource.");return ba(this,t)}}});var Fe,Ln=U(()=>{"use strict";yr();Fe=ze});var _r,_a,Ne,Be,Gn=U(()=>{"use strict";Vn();_r=(e,t)=>{(typeof Ue.trace>"u"?!Ue.wasm.trace:!Ue.trace)||console.timeStamp(`${e}::ORT::${t}`)},_a=(e,t)=>{let r=new Error().stack?.split(/\r\n|\r|\n/g)||[],n=!1;for(let o=0;o<r.length;o++){if(n&&!r[o].includes("TRACE_FUNC")){let i=`FUNC_${e}::${r[o].trim().split(" ")[1]}`;t&&(i+=`::${t}`),_r("CPU",i);return}r[o].includes("TRACE_FUNC")&&(n=!0)}},Ne=e=>{(typeof Ue.trace>"u"?!Ue.wasm.trace:!Ue.trace)||_a("BEGIN",e)},Be=e=>{(typeof Ue.trace>"u"?!Ue.wasm.trace:!Ue.trace)||_a("END",e)}});var wr,wa=U(()=>{"use strict";Nn();Ln();Gn();wr=class e{constructor(t){this.handler=t}async run(t,r,n){Ne();let o={},i={};if(typeof t!="object"||t===null||t instanceof Fe||Array.isArray(t))throw new TypeError("'feeds' must be an object that use input names as keys and OnnxValue as corresponding values.");let a=!0;if(typeof r=="object"){if(r===null)throw new TypeError("Unexpected argument[1]: cannot be null.");if(r instanceof Fe)throw new TypeError("'fetches' cannot be a Tensor");if(Array.isArray(r)){if(r.length===0)throw new TypeError("'fetches' cannot be an empty array.");a=!1;for(let p of r){if(typeof p!="string")throw new TypeError("'fetches' must be a string array or an object.");if(this.outputNames.indexOf(p)===-1)throw new RangeError(`'fetches' contains invalid output name: ${p}.`);o[p]=null}if(typeof n=="object"&&n!==null)i=n;else if(typeof n<"u")throw new TypeError("'options' must be an object.")}else{let p=!1,m=Object.getOwnPropertyNames(r);for(let u of this.outputNames)if(m.indexOf(u)!==-1){let h=r[u];(h===null||h instanceof Fe)&&(p=!0,a=!1,o[u]=h)}if(p){if(typeof n=="object"&&n!==null)i=n;else if(typeof n<"u")throw new TypeError("'options' must be an object.")}else i=r}}else if(typeof r<"u")throw new TypeError("Unexpected argument[1]: must be 'fetches' or 'options'.");for(let p of this.inputNames)if(typeof t[p]>"u")throw new Error(`input '${p}' is missing in 'feeds'.`);if(a)for(let p of this.outputNames)o[p]=null;let d=await this.handler.run(t,o,i),l={};for(let p in d)if(Object.hasOwnProperty.call(d,p)){let m=d[p];m instanceof Fe?l[p]=m:l[p]=new Fe(m.type,m.data,m.dims)}return Be(),l}async release(){return this.handler.dispose()}static async create(t,r,n,o){Ne();let i,a={};if(typeof t=="string"){if(i=t,typeof r=="object"&&r!==null)a=r;else if(typeof r<"u")throw new TypeError("'options' must be an object.")}else if(t instanceof Uint8Array){if(i=t,typeof r=="object"&&r!==null)a=r;else if(typeof r<"u")throw new TypeError("'options' must be an object.")}else if(t instanceof ArrayBuffer||typeof SharedArrayBuffer<"u"&&t instanceof SharedArrayBuffer){let m=t,u=0,h=t.byteLength;if(typeof r=="object"&&r!==null)a=r;else if(typeof r=="number"){if(u=r,!Number.isSafeInteger(u))throw new RangeError("'byteOffset' must be an integer.");if(u<0||u>=m.byteLength)throw new RangeError(`'byteOffset' is out of range [0, ${m.byteLength}).`);if(h=t.byteLength-u,typeof n=="number"){if(h=n,!Number.isSafeInteger(h))throw new RangeError("'byteLength' must be an integer.");if(h<=0||u+h>m.byteLength)throw new RangeError(`'byteLength' is out of range (0, ${m.byteLength-u}].`);if(typeof o=="object"&&o!==null)a=o;else if(typeof o<"u")throw new TypeError("'options' must be an object.")}else if(typeof n<"u")throw new TypeError("'byteLength' must be a number.")}else if(typeof r<"u")throw new TypeError("'options' must be an object.");i=new Uint8Array(m,u,h)}else throw new TypeError("Unexpected argument[0]: must be 'path' or 'buffer'.");let[d,l]=await Xi(a),p=await d.createInferenceSessionHandler(i,l);return Be(),new e(p)}startProfiling(){this.handler.startProfiling()}endProfiling(){this.handler.endProfiling()}get inputNames(){return this.handler.inputNames}get outputNames(){return this.handler.outputNames}}});var Fp,va=U(()=>{"use strict";wa();Fp=wr});var $a=U(()=>{"use strict"});var xa=U(()=>{"use strict"});var Sa=U(()=>{"use strict"});var Ta=U(()=>{"use strict"});var Hn={};Ht(Hn,{InferenceSession:()=>Fp,TRACE:()=>_r,TRACE_FUNC_BEGIN:()=>Ne,TRACE_FUNC_END:()=>Be,Tensor:()=>Fe,env:()=>_e,registerBackend:()=>Tt});var Le=U(()=>{"use strict";Ji();na();va();Ln();$a();xa();Gn();Sa();Ta()});var vr=U(()=>{"use strict"});var ka={};Ht(ka,{default:()=>qp});var Ca,Aa,qp,Ea=U(()=>{"use strict";Fn();gt();$r();Ca="ort-wasm-proxy-worker",Aa=globalThis.self?.name===Ca;Aa&&(self.onmessage=e=>{let{type:t,in:r}=e.data;try{switch(t){case"init-wasm":xr(r.wasm).then(()=>{Sr(r).then(()=>{postMessage({type:t})},n=>{postMessage({type:t,err:n})})},n=>{postMessage({type:t,err:n})});break;case"init-ep":{let{epName:n,env:o}=r;Tr(o,n).then(()=>{postMessage({type:t})},i=>{postMessage({type:t,err:i})});break}case"copy-from":{let{buffer:n}=r,o=qt(n);postMessage({type:t,out:o});break}case"create":{let{model:n,options:o}=r;Ir(n,o).then(i=>{postMessage({type:t,out:i})},i=>{postMessage({type:t,err:i})});break}case"release":Cr(r),postMessage({type:t});break;case"run":{let{sessionId:n,inputIndices:o,inputs:i,outputIndices:a,options:d}=r;Ar(n,o,i,a,new Array(a.length).fill(null),d).then(l=>{l.some(p=>p[3]!=="cpu")?postMessage({type:t,err:"Proxy does not support non-cpu tensor location."}):postMessage({type:t,out:l},Er([...i,...l]))},l=>{postMessage({type:t,err:l})});break}case"end-profiling":kr(r),postMessage({type:t});break;default:}}catch(n){postMessage({type:t,err:n})}});qp=Aa?null:e=>new Worker(e??Ve,{type:"module",name:Ca})});var za={};Ht(za,{default:()=>Kp});var qn,Pa,Kp,Oa=U(()=>{"use strict";Pa=(qn=import.meta.url,async function(e={}){function t(){return K.buffer!=Q.buffer&&pe(),Q}function r(){return K.buffer!=Q.buffer&&pe(),ie}function n(){return K.buffer!=Q.buffer&&pe(),te}function o(){return K.buffer!=Q.buffer&&pe(),be}function i(){return K.buffer!=Q.buffer&&pe(),Oe}function a(){return K.buffer!=Q.buffer&&pe(),ve}function d(){return K.buffer!=Q.buffer&&pe(),de}function l(){return K.buffer!=Q.buffer&&pe(),he}var p,m,u=Object.assign({},e),h=new Promise((s,c)=>{p=s,m=c}),_=typeof window=="object",y=typeof importScripts=="function",g=y&&self.name=="em-pthread";u.mountExternalData=(s,c)=>{s.startsWith("./")&&(s=s.substring(2)),(u.Fb||(u.Fb=new Map)).set(s,c)},u.unmountExternalData=()=>{delete u.Fb};var x=globalThis.SharedArrayBuffer??new WebAssembly.Memory({initial:0,maximum:0,shared:!0}).buffer.constructor;let $=()=>{let s=(f,b,w)=>(...I)=>{let O=Xe,B=b?.();I=f(...I);let G=b?.();return B!==G&&(f=G,w(B),b=w=null),Xe!=O?new Promise((F,X)=>{kn={resolve:F,reject:X}}):I},c=f=>async(...b)=>{try{if(u.Gb)throw Error("Session already started");let w=u.Gb={hc:b[0],errors:[]},I=await f(...b);if(u.Gb!==w)throw Error("Session mismatch");u.Hb?.flush();let O=w.errors;if(0<O.length){let B=await Promise.all(O);if(B=B.filter(G=>G),0<B.length)throw Error(B.join(`
`))}return I}finally{u.Gb=null}};u._OrtCreateSession=s(u._OrtCreateSession,()=>u._OrtCreateSession,f=>u._OrtCreateSession=f),u._OrtRun=c(s(u._OrtRun,()=>u._OrtRun,f=>u._OrtRun=f)),u._OrtRunWithBinding=c(s(u._OrtRunWithBinding,()=>u._OrtRunWithBinding,f=>u._OrtRunWithBinding=f)),u._OrtBindInput=s(u._OrtBindInput,()=>u._OrtBindInput,f=>u._OrtBindInput=f),$=void 0};u.jsepInit=(s,c)=>{if($?.(),s==="webgpu"){[u.Hb,u.Vb,u.Zb,u.Ob,u.Yb,u.kb,u.$b,u.cc,u.Wb,u.Xb,u.ac]=c;let f=u.Hb;u.jsepRegisterBuffer=(b,w,I,O)=>f.registerBuffer(b,w,I,O),u.jsepGetBuffer=b=>f.getBuffer(b),u.jsepCreateDownloader=(b,w,I)=>f.createDownloader(b,w,I),u.jsepOnCreateSession=b=>{f.onCreateSession(b)},u.jsepOnReleaseSession=b=>{f.onReleaseSession(b)},u.jsepOnRunStart=b=>f.onRunStart(b),u.dc=(b,w)=>{f.upload(b,w)}}else if(s==="webnn"){[u.Hb,u.bc,u.Pb,u.jsepEnsureTensor,u.ec,u.jsepDownloadTensor]=c,u.jsepReleaseTensorId=u.Pb;let f=u.Hb;u.jsepOnRunStart=b=>f.onRunStart(b),u.jsepRegisterMLContext=(b,w)=>{f.registerMLContext(b,w)},u.jsepOnReleaseSession=b=>{f.onReleaseSession(b)},u.jsepCreateMLTensorDownloader=(b,w)=>f.createMLTensorDownloader(b,w),u.jsepRegisterMLTensor=(b,w,I)=>f.registerMLTensor(b,w,I),u.jsepCreateMLContext=b=>f.createMLContext(b),u.jsepRegisterMLConstant=(b,w,I,O,B)=>f.registerMLConstant(b,w,I,O,B,u.Fb)}};var v,S,T=Object.assign({},u),A=(s,c)=>{throw c},C="";(_||y)&&(y?C=self.location.href:typeof document<"u"&&document.currentScript&&(C=document.currentScript.src),qn&&(C=qn),C=C.startsWith("blob:")?"":C.substr(0,C.replace(/[?#].*/,"").lastIndexOf("/")+1),y&&(S=s=>{var c=new XMLHttpRequest;return c.open("GET",s,!1),c.responseType="arraybuffer",c.send(null),new Uint8Array(c.response)}),v=(s,c,f)=>{var b=new XMLHttpRequest;b.open("GET",s,!0),b.responseType="arraybuffer",b.onload=()=>{b.status==200||b.status==0&&b.response?c(b.response):f()},b.onerror=f,b.send(null)});var P,D=console.log.bind(console),R=console.error.bind(console),H=D,L=R;if(Object.assign(u,T),T=null,g){let s=function(c){try{var f=c.data,b=f.cmd;if(b==="load"){let w=[];self.onmessage=I=>w.push(I),self.startWorker=()=>{postMessage({cmd:"loaded"});for(let I of w)s(I);self.onmessage=s};for(let I of f.handlers)u[I]&&!u[I].proxy||(u[I]=(...O)=>{postMessage({Nb:"callHandler",pc:I,args:O})},I=="print"&&(H=u[I]),I=="printErr"&&(L=u[I]));K=f.wasmMemory,pe(),re(f.wasmModule)}else if(b==="run"){On(f.pthread_ptr,0,0,1,0,0),Cn(f.pthread_ptr),xc(),Go(),V||(Vi(),V=!0);try{Sc(f.start_routine,f.arg)}catch(w){if(w!="unwind")throw w}}else b==="cancel"?Rt()&&fr(-1):f.target!=="setimmediate"&&(b==="checkMailbox"?V&&or():b&&(L(`worker: received unknown command ${b}`),L(f)))}catch(w){throw Wi(),w}};var wg=s,re,V=!1;L=function(...c){c=c.join(" "),console.error(c)},self.alert=function(...c){postMessage({Nb:"alert",text:c.join(" "),rc:Rt()})},u.instantiateWasm=(c,f)=>new Promise(b=>{re=w=>{w=new WebAssembly.Instance(w,Uo()),f(w),b()}}),self.onunhandledrejection=c=>{throw c.reason||c},self.onmessage=s}u.wasmBinary&&(P=u.wasmBinary);var K,we,j,Q,ie,te,be,Oe,ve,de,W,Y,he,De=!1;function pe(){var s=K.buffer;u.HEAP8=Q=new Int8Array(s),u.HEAP16=te=new Int16Array(s),u.HEAPU8=ie=new Uint8Array(s),u.HEAPU16=be=new Uint16Array(s),u.HEAP32=Oe=new Int32Array(s),u.HEAPU32=ve=new Uint32Array(s),u.HEAPF32=de=new Float32Array(s),u.HEAPF64=he=new Float64Array(s),u.HEAP64=W=new BigInt64Array(s),u.HEAPU64=Y=new BigUint64Array(s)}if(!g){if(!((K=new WebAssembly.Memory({initial:256,maximum:65536,shared:!0})).buffer instanceof x))throw L("requested a shared WebAssembly.Memory but the returned buffer is not a SharedArrayBuffer, indicating that while the browser has SharedArrayBuffer it does not have WebAssembly threads support - you may need to set a flag"),Error("bad memory");pe()}var Ie=[],He=[],mn=[],wt=0,fn=null,Gt=null;function Oo(){if(--wt==0&&(fn!==null&&(clearInterval(fn),fn=null),Gt)){var s=Gt;Gt=null,s()}}function ct(s){throw L(s="Aborted("+s+")"),De=!0,j=1,s=new WebAssembly.RuntimeError(s+". Build with -sASSERTIONS for more info."),m(s),s}var hn,Do=s=>s.startsWith("data:application/octet-stream;base64,"),Bo=s=>s.startsWith("file://");function Mo(s){if(s==hn&&P)return new Uint8Array(P);if(S)return S(s);throw"both async and sync fetching of the wasm failed"}function Ro(s,c,f){return function(b){if(!P&&(_||y)){if(typeof fetch=="function"&&!Bo(b))return fetch(b,{credentials:"same-origin"}).then(w=>{if(!w.ok)throw`failed to load wasm binary file at '${b}'`;return w.arrayBuffer()}).catch(()=>Mo(b));if(v)return new Promise((w,I)=>{v(b,O=>w(new Uint8Array(O)),I)})}return Promise.resolve().then(()=>Mo(b))}(s).then(b=>WebAssembly.instantiate(b,c)).then(f,b=>{L(`failed to asynchronously prepare wasm: ${b}`),ct(b)})}function Uo(){return{a:{O:$c,Aa:vc,b:Ic,aa:Ko,B:Zo,qa:Qo,Y:Jo,_:ei,ra:ti,oa:ri,ha:ni,na:oi,L:ii,Z:ai,W:si,pa:ui,X:di,va:Cc,F:kc,Q:Ec,P:zc,E:Dc,u:Bc,q:Mc,G:Rc,A:Hc,R:Fc,ua:qc,ka:Kc,U:jc,ba:Yc,H:Zc,ja:Cn,ta:Qc,t:Xc,Ba:Jc,x:rp,o:np,m:ip,c:Tn,n:ap,k:dp,w:lp,p:cp,f:pp,s:mp,l:fp,e:hp,j:gp,i:bp,g:yp,d:_p,ea:wp,fa:vp,ga:$p,ca:xi,da:Si,T:xp,h:Sp,D:Tp,I:Ip,M:Cp,y:Ap,sa:kp,V:Ep,v:Ii,z:Pp,N:zp,S:Op,za:Dp,ya:Bp,la:ki,ma:Ei,$:wn,C:Pi,K:zi,ia:Oi,J:Di,a:K,xa:_n,wa:Ri,r:Up}}}var gn={916868:(s,c,f,b,w)=>{if(u===void 0||!u.Fb)return 1;if((s=Ce(Number(s>>>0))).startsWith("./")&&(s=s.substring(2)),!(s=u.Fb.get(s)))return 2;if(c=Number(c>>>0),f=Number(f>>>0),b=Number(b>>>0),c+f>s.byteLength)return 3;try{let I=s.subarray(c,c+f);switch(w){case 0:r().set(I,b>>>0);break;case 1:u.dc(b,I);break;default:return 4}return 0}catch{return 4}},917583:(s,c,f)=>{u.ec(s,r().subarray(c>>>0,c+f>>>0))},917646:()=>u.bc(),917687:s=>{u.Pb(s)},917723:()=>{u.Wb()},917754:()=>{u.Xb()},917783:()=>{u.ac()},917808:s=>u.Vb(s),917841:s=>u.Zb(s),917873:(s,c,f)=>{u.Ob(Number(s),Number(c),Number(f),!0)},917936:(s,c,f)=>{u.Ob(Number(s),Number(c),Number(f))},917993:()=>typeof wasmOffsetConverter<"u",918050:s=>{u.kb("Abs",s,void 0)},918101:s=>{u.kb("Neg",s,void 0)},918152:s=>{u.kb("Floor",s,void 0)},918205:s=>{u.kb("Ceil",s,void 0)},918257:s=>{u.kb("Reciprocal",s,void 0)},918315:s=>{u.kb("Sqrt",s,void 0)},918367:s=>{u.kb("Exp",s,void 0)},918418:s=>{u.kb("Erf",s,void 0)},918469:s=>{u.kb("Sigmoid",s,void 0)},918524:(s,c,f)=>{u.kb("HardSigmoid",s,{alpha:c,beta:f})},918603:s=>{u.kb("Log",s,void 0)},918654:s=>{u.kb("Sin",s,void 0)},918705:s=>{u.kb("Cos",s,void 0)},918756:s=>{u.kb("Tan",s,void 0)},918807:s=>{u.kb("Asin",s,void 0)},918859:s=>{u.kb("Acos",s,void 0)},918911:s=>{u.kb("Atan",s,void 0)},918963:s=>{u.kb("Sinh",s,void 0)},919015:s=>{u.kb("Cosh",s,void 0)},919067:s=>{u.kb("Asinh",s,void 0)},919120:s=>{u.kb("Acosh",s,void 0)},919173:s=>{u.kb("Atanh",s,void 0)},919226:s=>{u.kb("Tanh",s,void 0)},919278:s=>{u.kb("Not",s,void 0)},919329:(s,c,f)=>{u.kb("Clip",s,{min:c,max:f})},919398:s=>{u.kb("Clip",s,void 0)},919450:(s,c)=>{u.kb("Elu",s,{alpha:c})},919508:s=>{u.kb("Gelu",s,void 0)},919560:s=>{u.kb("Relu",s,void 0)},919612:(s,c)=>{u.kb("LeakyRelu",s,{alpha:c})},919676:(s,c)=>{u.kb("ThresholdedRelu",s,{alpha:c})},919746:(s,c)=>{u.kb("Cast",s,{to:c})},919804:s=>{u.kb("Add",s,void 0)},919855:s=>{u.kb("Sub",s,void 0)},919906:s=>{u.kb("Mul",s,void 0)},919957:s=>{u.kb("Div",s,void 0)},920008:s=>{u.kb("Pow",s,void 0)},920059:s=>{u.kb("Equal",s,void 0)},920112:s=>{u.kb("Greater",s,void 0)},920167:s=>{u.kb("GreaterOrEqual",s,void 0)},920229:s=>{u.kb("Less",s,void 0)},920281:s=>{u.kb("LessOrEqual",s,void 0)},920340:(s,c,f,b,w)=>{u.kb("ReduceMean",s,{keepDims:!!c,noopWithEmptyAxes:!!f,axes:b?Array.from(i().subarray(Number(b)>>>0,Number(w)>>>0)):[]})},920515:(s,c,f,b,w)=>{u.kb("ReduceMax",s,{keepDims:!!c,noopWithEmptyAxes:!!f,axes:b?Array.from(i().subarray(Number(b)>>>0,Number(w)>>>0)):[]})},920689:(s,c,f,b,w)=>{u.kb("ReduceMin",s,{keepDims:!!c,noopWithEmptyAxes:!!f,axes:b?Array.from(i().subarray(Number(b)>>>0,Number(w)>>>0)):[]})},920863:(s,c,f,b,w)=>{u.kb("ReduceProd",s,{keepDims:!!c,noopWithEmptyAxes:!!f,axes:b?Array.from(i().subarray(Number(b)>>>0,Number(w)>>>0)):[]})},921038:(s,c,f,b,w)=>{u.kb("ReduceSum",s,{keepDims:!!c,noopWithEmptyAxes:!!f,axes:b?Array.from(i().subarray(Number(b)>>>0,Number(w)>>>0)):[]})},921212:(s,c,f,b,w)=>{u.kb("ReduceL1",s,{keepDims:!!c,noopWithEmptyAxes:!!f,axes:b?Array.from(i().subarray(Number(b)>>>0,Number(w)>>>0)):[]})},921385:(s,c,f,b,w)=>{u.kb("ReduceL2",s,{keepDims:!!c,noopWithEmptyAxes:!!f,axes:b?Array.from(i().subarray(Number(b)>>>0,Number(w)>>>0)):[]})},921558:(s,c,f,b,w)=>{u.kb("ReduceLogSum",s,{keepDims:!!c,noopWithEmptyAxes:!!f,axes:b?Array.from(i().subarray(Number(b)>>>0,Number(w)>>>0)):[]})},921735:(s,c,f,b,w)=>{u.kb("ReduceSumSquare",s,{keepDims:!!c,noopWithEmptyAxes:!!f,axes:b?Array.from(i().subarray(Number(b)>>>0,Number(w)>>>0)):[]})},921915:(s,c,f,b,w)=>{u.kb("ReduceLogSumExp",s,{keepDims:!!c,noopWithEmptyAxes:!!f,axes:b?Array.from(i().subarray(Number(b)>>>0,Number(w)>>>0)):[]})},922095:s=>{u.kb("Where",s,void 0)},922148:(s,c,f)=>{u.kb("Transpose",s,{perm:c?Array.from(i().subarray(Number(c)>>>0,Number(f)>>>0)):[]})},922272:(s,c,f,b)=>{u.kb("DepthToSpace",s,{blocksize:c,mode:Ce(f),format:b?"NHWC":"NCHW"})},922405:(s,c,f,b)=>{u.kb("DepthToSpace",s,{blocksize:c,mode:Ce(f),format:b?"NHWC":"NCHW"})},922538:(s,c,f,b,w,I,O,B,G,F,X,le,ge,z,ue)=>{u.kb("ConvTranspose",s,{format:G?"NHWC":"NCHW",autoPad:c,dilations:[f],group:b,kernelShape:[w],pads:[I,O],strides:[B],wIsConst:()=>!!t()[F>>>0],outputPadding:X?Array.from(i().subarray(Number(X)>>>0,Number(le)>>>0)):[],outputShape:ge?Array.from(i().subarray(Number(ge)>>>0,Number(z)>>>0)):[],activation:Ce(ue)})},922971:(s,c,f,b,w,I,O,B,G,F,X,le,ge,z)=>{u.kb("ConvTranspose",s,{format:B?"NHWC":"NCHW",autoPad:c,dilations:Array.from(i().subarray(Number(f)>>>0,2+(Number(f)>>>0)>>>0)),group:b,kernelShape:Array.from(i().subarray(Number(w)>>>0,2+(Number(w)>>>0)>>>0)),pads:Array.from(i().subarray(Number(I)>>>0,4+(Number(I)>>>0)>>>0)),strides:Array.from(i().subarray(Number(O)>>>0,2+(Number(O)>>>0)>>>0)),wIsConst:()=>!!t()[G>>>0],outputPadding:F?Array.from(i().subarray(Number(F)>>>0,Number(X)>>>0)):[],outputShape:le?Array.from(i().subarray(Number(le)>>>0,Number(ge)>>>0)):[],activation:Ce(z)})},923632:(s,c,f,b,w,I,O,B,G,F,X,le,ge,z,ue)=>{u.kb("ConvTranspose",s,{format:G?"NHWC":"NCHW",autoPad:c,dilations:[f],group:b,kernelShape:[w],pads:[I,O],strides:[B],wIsConst:()=>!!t()[F>>>0],outputPadding:X?Array.from(i().subarray(Number(X)>>>0,Number(le)>>>0)):[],outputShape:ge?Array.from(i().subarray(Number(ge)>>>0,Number(z)>>>0)):[],activation:Ce(ue)})},924065:(s,c,f,b,w,I,O,B,G,F,X,le,ge,z)=>{u.kb("ConvTranspose",s,{format:B?"NHWC":"NCHW",autoPad:c,dilations:Array.from(i().subarray(Number(f)>>>0,2+(Number(f)>>>0)>>>0)),group:b,kernelShape:Array.from(i().subarray(Number(w)>>>0,2+(Number(w)>>>0)>>>0)),pads:Array.from(i().subarray(Number(I)>>>0,4+(Number(I)>>>0)>>>0)),strides:Array.from(i().subarray(Number(O)>>>0,2+(Number(O)>>>0)>>>0)),wIsConst:()=>!!t()[G>>>0],outputPadding:F?Array.from(i().subarray(Number(F)>>>0,Number(X)>>>0)):[],outputShape:le?Array.from(i().subarray(Number(le)>>>0,Number(ge)>>>0)):[],activation:Ce(z)})},924726:(s,c)=>{u.kb("GlobalAveragePool",s,{format:c?"NHWC":"NCHW"})},924817:(s,c,f,b,w,I,O,B,G,F,X,le,ge,z)=>{u.kb("AveragePool",s,{format:z?"NHWC":"NCHW",auto_pad:c,ceil_mode:f,count_include_pad:b,storage_order:w,dilations:I?Array.from(i().subarray(Number(I)>>>0,Number(O)>>>0)):[],kernel_shape:B?Array.from(i().subarray(Number(B)>>>0,Number(G)>>>0)):[],pads:F?Array.from(i().subarray(Number(F)>>>0,Number(X)>>>0)):[],strides:le?Array.from(i().subarray(Number(le)>>>0,Number(ge)>>>0)):[]})},925296:(s,c)=>{u.kb("GlobalAveragePool",s,{format:c?"NHWC":"NCHW"})},925387:(s,c,f,b,w,I,O,B,G,F,X,le,ge,z)=>{u.kb("AveragePool",s,{format:z?"NHWC":"NCHW",auto_pad:c,ceil_mode:f,count_include_pad:b,storage_order:w,dilations:I?Array.from(i().subarray(Number(I)>>>0,Number(O)>>>0)):[],kernel_shape:B?Array.from(i().subarray(Number(B)>>>0,Number(G)>>>0)):[],pads:F?Array.from(i().subarray(Number(F)>>>0,Number(X)>>>0)):[],strides:le?Array.from(i().subarray(Number(le)>>>0,Number(ge)>>>0)):[]})},925866:(s,c)=>{u.kb("GlobalMaxPool",s,{format:c?"NHWC":"NCHW"})},925953:(s,c,f,b,w,I,O,B,G,F,X,le,ge,z)=>{u.kb("MaxPool",s,{format:z?"NHWC":"NCHW",auto_pad:c,ceil_mode:f,count_include_pad:b,storage_order:w,dilations:I?Array.from(i().subarray(Number(I)>>>0,Number(O)>>>0)):[],kernel_shape:B?Array.from(i().subarray(Number(B)>>>0,Number(G)>>>0)):[],pads:F?Array.from(i().subarray(Number(F)>>>0,Number(X)>>>0)):[],strides:le?Array.from(i().subarray(Number(le)>>>0,Number(ge)>>>0)):[]})},926428:(s,c)=>{u.kb("GlobalMaxPool",s,{format:c?"NHWC":"NCHW"})},926515:(s,c,f,b,w,I,O,B,G,F,X,le,ge,z)=>{u.kb("MaxPool",s,{format:z?"NHWC":"NCHW",auto_pad:c,ceil_mode:f,count_include_pad:b,storage_order:w,dilations:I?Array.from(i().subarray(Number(I)>>>0,Number(O)>>>0)):[],kernel_shape:B?Array.from(i().subarray(Number(B)>>>0,Number(G)>>>0)):[],pads:F?Array.from(i().subarray(Number(F)>>>0,Number(X)>>>0)):[],strides:le?Array.from(i().subarray(Number(le)>>>0,Number(ge)>>>0)):[]})},926990:(s,c,f,b,w)=>{u.kb("Gemm",s,{alpha:c,beta:f,transA:b,transB:w})},927094:s=>{u.kb("MatMul",s,void 0)},927148:(s,c,f,b)=>{u.kb("ArgMax",s,{keepDims:!!c,selectLastIndex:!!f,axis:b})},927256:(s,c,f,b)=>{u.kb("ArgMin",s,{keepDims:!!c,selectLastIndex:!!f,axis:b})},927364:(s,c)=>{u.kb("Softmax",s,{axis:c})},927427:(s,c)=>{u.kb("Concat",s,{axis:c})},927487:(s,c,f,b,w)=>{u.kb("Split",s,{axis:c,numOutputs:f,splitSizes:b?Array.from(i().subarray(Number(b)>>>0,Number(w)>>>0)):[]})},927643:s=>{u.kb("Expand",s,void 0)},927697:(s,c)=>{u.kb("Gather",s,{axis:Number(c)})},927768:(s,c)=>{u.kb("GatherElements",s,{axis:Number(c)})},927847:(s,c)=>{u.kb("GatherND",s,{batch_dims:Number(c)})},927926:(s,c,f,b,w,I,O,B,G,F,X)=>{u.kb("Resize",s,{antialias:c,axes:f?Array.from(i().subarray(Number(f)>>>0,Number(b)>>>0)):[],coordinateTransformMode:Ce(w),cubicCoeffA:I,excludeOutside:O,extrapolationValue:B,keepAspectRatioPolicy:Ce(G),mode:Ce(F),nearestMode:Ce(X)})},928288:(s,c,f,b,w,I,O)=>{u.kb("Slice",s,{starts:c?Array.from(i().subarray(Number(c)>>>0,Number(f)>>>0)):[],ends:b?Array.from(i().subarray(Number(b)>>>0,Number(w)>>>0)):[],axes:I?Array.from(i().subarray(Number(I)>>>0,Number(O)>>>0)):[]})},928552:s=>{u.kb("Tile",s,void 0)},928604:(s,c,f)=>{u.kb("InstanceNormalization",s,{epsilon:c,format:f?"NHWC":"NCHW"})},928718:(s,c,f)=>{u.kb("InstanceNormalization",s,{epsilon:c,format:f?"NHWC":"NCHW"})},928832:s=>{u.kb("Range",s,void 0)},928885:(s,c)=>{u.kb("Einsum",s,{equation:Ce(c)})},928966:(s,c,f,b,w)=>{u.kb("Pad",s,{mode:c,value:f,pads:b?Array.from(i().subarray(Number(b)>>>0,Number(w)>>>0)):[]})},929109:(s,c,f,b,w,I)=>{u.kb("BatchNormalization",s,{epsilon:c,momentum:f,spatial:!!w,trainingMode:!!b,format:I?"NHWC":"NCHW"})},929278:(s,c,f,b,w,I)=>{u.kb("BatchNormalization",s,{epsilon:c,momentum:f,spatial:!!w,trainingMode:!!b,format:I?"NHWC":"NCHW"})},929447:(s,c,f)=>{u.kb("CumSum",s,{exclusive:Number(c),reverse:Number(f)})},929544:(s,c,f)=>{u.kb("DequantizeLinear",s,{axis:c,blockSize:f})},929634:(s,c,f,b,w)=>{u.kb("GridSample",s,{align_corners:c,mode:Ce(f),padding_mode:Ce(b),format:w?"NHWC":"NCHW"})},929804:(s,c,f,b,w)=>{u.kb("GridSample",s,{align_corners:c,mode:Ce(f),padding_mode:Ce(b),format:w?"NHWC":"NCHW"})},929974:(s,c,f,b,w,I,O,B,G)=>{u.kb("Attention",s,{numHeads:c,isUnidirectional:f,maskFilterValue:b,scale:w,doRotary:I,qkvHiddenSizes:O?Array.from(i().subarray(Number(B)>>>0,Number(B)+O>>>0)):[],pastPresentShareBuffer:!!G})},930246:s=>{u.kb("BiasAdd",s,void 0)},930301:s=>{u.kb("BiasSplitGelu",s,void 0)},930362:s=>{u.kb("FastGelu",s,void 0)},930418:(s,c,f,b,w,I,O,B,G,F,X,le,ge,z,ue,Se)=>{u.kb("Conv",s,{format:le?"NHWC":"NCHW",auto_pad:c,dilations:f?Array.from(i().subarray(Number(f)>>>0,Number(b)>>>0)):[],group:w,kernel_shape:I?Array.from(i().subarray(Number(I)>>>0,Number(O)>>>0)):[],pads:B?Array.from(i().subarray(Number(B)>>>0,Number(G)>>>0)):[],strides:F?Array.from(i().subarray(Number(F)>>>0,Number(X)>>>0)):[],w_is_const:()=>!!t()[Number(ge)>>>0],activation:Ce(z),activation_params:ue?Array.from(d().subarray(Number(ue)>>>0,Number(Se)>>>0)):[]})},931002:s=>{u.kb("Gelu",s,void 0)},931054:(s,c,f,b,w,I,O,B,G)=>{u.kb("GroupQueryAttention",s,{numHeads:c,kvNumHeads:f,scale:b,softcap:w,doRotary:I,rotaryInterleaved:O,smoothSoftmax:B,localWindowSize:G})},931271:(s,c,f,b)=>{u.kb("LayerNormalization",s,{axis:c,epsilon:f,simplified:!!b})},931382:(s,c,f,b)=>{u.kb("LayerNormalization",s,{axis:c,epsilon:f,simplified:!!b})},931493:(s,c,f,b,w,I)=>{u.kb("MatMulNBits",s,{k:c,n:f,accuracyLevel:b,bits:w,blockSize:I})},931620:(s,c,f,b,w,I)=>{u.kb("MultiHeadAttention",s,{numHeads:c,isUnidirectional:f,maskFilterValue:b,scale:w,doRotary:I})},931779:(s,c)=>{u.kb("QuickGelu",s,{alpha:c})},931843:(s,c,f,b,w)=>{u.kb("RotaryEmbedding",s,{interleaved:!!c,numHeads:f,rotaryEmbeddingDim:b,scale:w})},931982:(s,c,f)=>{u.kb("SkipLayerNormalization",s,{epsilon:c,simplified:!!f})},932084:(s,c,f)=>{u.kb("SkipLayerNormalization",s,{epsilon:c,simplified:!!f})},932186:(s,c,f,b)=>{u.kb("GatherBlockQuantized",s,{gatherAxis:c,quantizeAxis:f,blockSize:b})},932307:s=>{u.$b(s)},932341:(s,c)=>u.cc(Number(s),Number(c),u.Gb.hc,u.Gb.errors)};function vc(s,c,f){return yi(async()=>{await u.Yb(Number(s),Number(c),Number(f))})}function $c(){return typeof wasmOffsetConverter<"u"}function bn(s){this.name="ExitStatus",this.message=`Program terminated with exit(${s})`,this.status=s}var yn=s=>{s.terminate(),s.onmessage=()=>{}},No=s=>{pt.length==0&&(Fo(),Ho(pt[0]));var c=pt.pop();if(!c)return 6;$t.push(c),Ze[s.Bb]=c,c.Bb=s.Bb;var f={cmd:"run",start_routine:s.ic,arg:s.Rb,pthread_ptr:s.Bb};return c.postMessage(f,s.nc),0},vt=0,$e=(s,c,...f)=>{for(var b=2*f.length,w=Mn(),I=Bn(8*b),O=I>>>3,B=0;B<f.length;B++){var G=f[B];typeof G=="bigint"?(W[O+2*B]=1n,W[O+2*B+1]=G):(W[O+2*B]=0n,l()[O+2*B+1>>>0]=G)}return s=Li(s,0,b,I,c),hr(w),s};function _n(s){if(g)return $e(0,1,s);if(j=s,!(0<vt)){for(var c of $t)yn(c);for(c of pt)yn(c);pt=[],$t=[],Ze=[],De=!0}A(0,new bn(s))}function Vo(s){if(g)return $e(1,0,s);wn(s)}var wn=s=>{if(j=s,g)throw Vo(s),"unwind";_n(s)},pt=[],$t=[],Wo=[],Ze={},Lo=s=>{var c=s.Bb;delete Ze[c],pt.push(s),$t.splice($t.indexOf(s),1),s.Bb=0,Dn(c)};function Go(){Wo.forEach(s=>s())}var Ho=s=>new Promise(c=>{s.onmessage=w=>{var I=(w=w.data).cmd;if(w.targetThread&&w.targetThread!=Rt()){var O=Ze[w.targetThread];O?O.postMessage(w,w.transferList):L(`Internal error! Worker sent a message "${I}" to target pthread ${w.targetThread}, but that thread no longer exists!`)}else I==="checkMailbox"?or():I==="spawnThread"?No(w):I==="cleanupThread"?Lo(Ze[w.thread]):I==="killThread"?(w=w.thread,I=Ze[w],delete Ze[w],yn(I),Dn(w),$t.splice($t.indexOf(I),1),I.Bb=0):I==="cancelThread"?Ze[w.thread].postMessage({cmd:"cancel"}):I==="loaded"?(s.loaded=!0,c(s)):I==="alert"?alert(`Thread ${w.threadId}: ${w.text}`):w.target==="setimmediate"?s.postMessage(w):I==="callHandler"?u[w.handler](...w.args):I&&L(`worker sent an unknown command ${I}`)},s.onerror=w=>{throw L(`worker sent an error! ${w.filename}:${w.lineno}: ${w.message}`),w};var f,b=[];for(f of[])u.hasOwnProperty(f)&&b.push(f);s.postMessage({cmd:"load",handlers:b,wasmMemory:K,wasmModule:we})});function Fo(){var s=new Worker(import.meta.url.startsWith("file:")?new URL("ort.bundle.min.mjs",import.meta.url):new URL(import.meta.url),{type:"module",workerData:"em-pthread",name:"em-pthread"});pt.push(s)}var nr=s=>{for(;0<s.length;)s.shift()(u)},xc=()=>{var s=Rt(),c=a()[s+52>>>2>>>0];s=a()[s+56>>>2>>>0],Hi(c,c-s),hr(c)},Sc=(s,c)=>{vt=0,s=Fi(s,c),0<vt?j=s:fr(s)};class Tc{constructor(c){this.Kb=c-24}}function Ic(s,c,f){var b=new Tc(s>>>=0);throw c>>>=0,f>>>=0,a()[b.Kb+16>>>2>>>0]=0,a()[b.Kb+4>>>2>>>0]=c,a()[b.Kb+8>>>2>>>0]=f,s}function qo(s,c,f,b){return g?$e(2,1,s,c,f,b):Ko(s,c,f,b)}function Ko(s,c,f,b){if(s>>>=0,c>>>=0,f>>>=0,b>>>=0,x===void 0)return L("Current environment does not support SharedArrayBuffer, pthreads are not available!"),6;var w=[];return g&&w.length===0?qo(s,c,f,b):(s={ic:f,Bb:s,Rb:b,nc:w},g?(s.Nb="spawnThread",postMessage(s,w),0):No(s))}var jo=typeof TextDecoder<"u"?new TextDecoder("utf8"):void 0,Yo=(s,c,f)=>{var b=(c>>>=0)+f;for(f=c;s[f]&&!(f>=b);)++f;if(16<f-c&&s.buffer&&jo)return jo.decode(s.buffer instanceof x?s.slice(c,f):s.subarray(c,f));for(b="";c<f;){var w=s[c++];if(128&w){var I=63&s[c++];if((224&w)==192)b+=String.fromCharCode((31&w)<<6|I);else{var O=63&s[c++];65536>(w=(240&w)==224?(15&w)<<12|I<<6|O:(7&w)<<18|I<<12|O<<6|63&s[c++])?b+=String.fromCharCode(w):(w-=65536,b+=String.fromCharCode(55296|w>>10,56320|1023&w))}}else b+=String.fromCharCode(w)}return b},Ce=(s,c)=>(s>>>=0)?Yo(r(),s,c):"";function Zo(s,c,f){return g?$e(3,1,s,c,f):0}function Qo(s,c){if(g)return $e(4,1,s,c)}var vn=s=>{for(var c=0,f=0;f<s.length;++f){var b=s.charCodeAt(f);127>=b?c++:2047>=b?c+=2:55296<=b&&57343>=b?(c+=4,++f):c+=3}return c},Xo=(s,c,f,b)=>{if(!(0<b))return 0;var w=f>>>=0;b=f+b-1;for(var I=0;I<s.length;++I){var O=s.charCodeAt(I);if(55296<=O&&57343>=O&&(O=65536+((1023&O)<<10)|1023&s.charCodeAt(++I)),127>=O){if(f>=b)break;c[f++>>>0]=O}else{if(2047>=O){if(f+1>=b)break;c[f++>>>0]=192|O>>6}else{if(65535>=O){if(f+2>=b)break;c[f++>>>0]=224|O>>12}else{if(f+3>=b)break;c[f++>>>0]=240|O>>18,c[f++>>>0]=128|O>>12&63}c[f++>>>0]=128|O>>6&63}c[f++>>>0]=128|63&O}}return c[f>>>0]=0,f-w},Dt=(s,c,f)=>Xo(s,r(),c,f);function Jo(s,c){if(g)return $e(5,1,s,c)}function ei(s,c,f){if(g)return $e(6,1,s,c,f)}function ti(s,c,f){return g?$e(7,1,s,c,f):0}function ri(s,c){if(g)return $e(8,1,s,c)}function ni(s,c,f){if(g)return $e(9,1,s,c,f)}function oi(s,c,f,b){if(g)return $e(10,1,s,c,f,b)}function ii(s,c,f,b){if(g)return $e(11,1,s,c,f,b)}function ai(s,c,f,b){if(g)return $e(12,1,s,c,f,b)}function si(s){if(g)return $e(13,1,s)}function ui(s,c){if(g)return $e(14,1,s,c)}function di(s,c,f){if(g)return $e(15,1,s,c,f)}var li,mt,Cc=()=>{ct("")},Qe=s=>{for(var c="";r()[s>>>0];)c+=li[r()[s++>>>0]];return c},$n={},xn={},Ac={};function st(s,c,f={}){if(!("argPackAdvance"in c))throw new TypeError("registerType registeredInstance requires argPackAdvance");return function(b,w,I={}){var O=w.name;if(!b)throw new mt(`type "${O}" must have a positive integer typeid pointer`);if(xn.hasOwnProperty(b)){if(I.Tb)return;throw new mt(`Cannot register type '${O}' twice`)}xn[b]=w,delete Ac[b],$n.hasOwnProperty(b)&&(w=$n[b],delete $n[b],w.forEach(B=>B()))}(s,c,f)}var ci=(s,c,f)=>{switch(c){case 1:return f?b=>t()[b>>>0]:b=>r()[b>>>0];case 2:return f?b=>n()[b>>>1>>>0]:b=>o()[b>>>1>>>0];case 4:return f?b=>i()[b>>>2>>>0]:b=>a()[b>>>2>>>0];case 8:return f?b=>W[b>>>3]:b=>Y[b>>>3];default:throw new TypeError(`invalid integer width (${c}): ${s}`)}};function kc(s,c,f){f>>>=0,st(s>>>=0,{name:c=Qe(c>>>0),fromWireType:b=>b,toWireType:function(b,w){if(typeof w!="bigint"&&typeof w!="number")throw w=w===null?"null":(b=typeof w)=="object"||b==="array"||b==="function"?w.toString():""+w,new TypeError(`Cannot convert "${w}" to ${this.name}`);return typeof w=="number"&&(w=BigInt(w)),w},argPackAdvance:ft,readValueFromPointer:ci(c,f,c.indexOf("u")==-1),Eb:null})}var ft=8;function Ec(s,c,f,b){st(s>>>=0,{name:c=Qe(c>>>0),fromWireType:function(w){return!!w},toWireType:function(w,I){return I?f:b},argPackAdvance:ft,readValueFromPointer:function(w){return this.fromWireType(r()[w>>>0])},Eb:null})}var Sn=[],ut=[];function Tn(s){9<(s>>>=0)&&--ut[s+1]==0&&(ut[s]=void 0,Sn.push(s))}var Re=s=>{if(!s)throw new mt("Cannot use deleted val. handle = "+s);return ut[s]},We=s=>{switch(s){case void 0:return 2;case null:return 4;case!0:return 6;case!1:return 8;default:let c=Sn.pop()||ut.length;return ut[c]=s,ut[c+1]=1,c}};function In(s){return this.fromWireType(a()[s>>>2>>>0])}var Pc={name:"emscripten::val",fromWireType:s=>{var c=Re(s);return Tn(s),c},toWireType:(s,c)=>We(c),argPackAdvance:ft,readValueFromPointer:In,Eb:null};function zc(s){return st(s>>>0,Pc)}var Oc=(s,c)=>{switch(c){case 4:return function(f){return this.fromWireType(d()[f>>>2>>>0])};case 8:return function(f){return this.fromWireType(l()[f>>>3>>>0])};default:throw new TypeError(`invalid float width (${c}): ${s}`)}};function Dc(s,c,f){f>>>=0,st(s>>>=0,{name:c=Qe(c>>>0),fromWireType:b=>b,toWireType:(b,w)=>w,argPackAdvance:ft,readValueFromPointer:Oc(c,f),Eb:null})}function Bc(s,c,f,b,w){if(s>>>=0,f>>>=0,c=Qe(c>>>0),w===-1&&(w=4294967295),w=B=>B,b===0){var I=32-8*f;w=B=>B<<I>>>I}var O=c.includes("unsigned")?function(B,G){return G>>>0}:function(B,G){return G};st(s,{name:c,fromWireType:w,toWireType:O,argPackAdvance:ft,readValueFromPointer:ci(c,f,b!==0),Eb:null})}function Mc(s,c,f){function b(I){var O=a()[I>>>2>>>0];return I=a()[I+4>>>2>>>0],new w(t().buffer,I,O)}var w=[Int8Array,Uint8Array,Int16Array,Uint16Array,Int32Array,Uint32Array,Float32Array,Float64Array,BigInt64Array,BigUint64Array][c];st(s>>>=0,{name:f=Qe(f>>>0),fromWireType:b,argPackAdvance:ft,readValueFromPointer:b},{Tb:!0})}function Rc(s,c){s>>>=0;var f=(c=Qe(c>>>0))==="std::string";st(s,{name:c,fromWireType:function(b){var w=a()[b>>>2>>>0],I=b+4;if(f)for(var O=I,B=0;B<=w;++B){var G=I+B;if(B==w||r()[G>>>0]==0){if(O=Ce(O,G-O),F===void 0)var F=O;else F+=String.fromCharCode(0),F+=O;O=G+1}}else{for(F=Array(w),B=0;B<w;++B)F[B]=String.fromCharCode(r()[I+B>>>0]);F=F.join("")}return Je(b),F},toWireType:function(b,w){w instanceof ArrayBuffer&&(w=new Uint8Array(w));var I=typeof w=="string";if(!(I||w instanceof Uint8Array||w instanceof Uint8ClampedArray||w instanceof Int8Array))throw new mt("Cannot pass non-string to std::string");var O=f&&I?vn(w):w.length,B=mr(4+O+1),G=B+4;if(a()[B>>>2>>>0]=O,f&&I)Dt(w,G,O+1);else if(I)for(I=0;I<O;++I){var F=w.charCodeAt(I);if(255<F)throw Je(G),new mt("String has UTF-16 code units that do not fit in 8 bits");r()[G+I>>>0]=F}else for(I=0;I<O;++I)r()[G+I>>>0]=w[I];return b!==null&&b.push(Je,B),B},argPackAdvance:ft,readValueFromPointer:In,Eb(b){Je(b)}})}var pi=typeof TextDecoder<"u"?new TextDecoder("utf-16le"):void 0,Uc=(s,c)=>{for(var f=s>>1,b=f+c/2;!(f>=b)&&o()[f>>>0];)++f;if(32<(f<<=1)-s&&pi)return pi.decode(r().slice(s,f));for(f="",b=0;!(b>=c/2);++b){var w=n()[s+2*b>>>1>>>0];if(w==0)break;f+=String.fromCharCode(w)}return f},Nc=(s,c,f)=>{if(f??=2147483647,2>f)return 0;var b=c;f=(f-=2)<2*s.length?f/2:s.length;for(var w=0;w<f;++w){var I=s.charCodeAt(w);n()[c>>>1>>>0]=I,c+=2}return n()[c>>>1>>>0]=0,c-b},Vc=s=>2*s.length,Wc=(s,c)=>{for(var f=0,b="";!(f>=c/4);){var w=i()[s+4*f>>>2>>>0];if(w==0)break;++f,65536<=w?(w-=65536,b+=String.fromCharCode(55296|w>>10,56320|1023&w)):b+=String.fromCharCode(w)}return b},Lc=(s,c,f)=>{if(c>>>=0,f??=2147483647,4>f)return 0;var b=c;f=b+f-4;for(var w=0;w<s.length;++w){var I=s.charCodeAt(w);if(55296<=I&&57343>=I&&(I=65536+((1023&I)<<10)|1023&s.charCodeAt(++w)),i()[c>>>2>>>0]=I,(c+=4)+4>f)break}return i()[c>>>2>>>0]=0,c-b},Gc=s=>{for(var c=0,f=0;f<s.length;++f){var b=s.charCodeAt(f);55296<=b&&57343>=b&&++f,c+=4}return c};function Hc(s,c,f){if(s>>>=0,c>>>=0,f=Qe(f>>>=0),c===2)var b=Uc,w=Nc,I=Vc,O=B=>o()[B>>>1>>>0];else c===4&&(b=Wc,w=Lc,I=Gc,O=B=>a()[B>>>2>>>0]);st(s,{name:f,fromWireType:B=>{for(var G,F=a()[B>>>2>>>0],X=B+4,le=0;le<=F;++le){var ge=B+4+le*c;le!=F&&O(ge)!=0||(X=b(X,ge-X),G===void 0?G=X:(G+=String.fromCharCode(0),G+=X),X=ge+c)}return Je(B),G},toWireType:(B,G)=>{if(typeof G!="string")throw new mt(`Cannot pass non-string to C++ string type ${f}`);var F=I(G),X=mr(4+F+c);return a()[X>>>2>>>0]=F/c,w(G,X+4,F+c),B!==null&&B.push(Je,X),X},argPackAdvance:ft,readValueFromPointer:In,Eb(B){Je(B)}})}function Fc(s,c){st(s>>>=0,{Ub:!0,name:c=Qe(c>>>0),argPackAdvance:0,fromWireType:()=>{},toWireType:()=>{}})}var qc=()=>1;function Kc(s){On(s>>>0,!y,1,!_,131072,!1),Go()}var mi=s=>{if(!De)try{if(s(),!(0<vt))try{g?fr(j):wn(j)}catch(c){c instanceof bn||c=="unwind"||A(0,c)}}catch(c){c instanceof bn||c=="unwind"||A(0,c)}};function Cn(s){s>>>=0,typeof Atomics.oc=="function"&&(Atomics.oc(i(),s>>>2,s).value.then(or),s+=128,Atomics.store(i(),s>>>2,1))}var or=()=>{var s=Rt();s&&(Cn(s),mi(Gi))};function jc(s,c){(s>>>=0)==c>>>0?setTimeout(or):g?postMessage({targetThread:s,cmd:"checkMailbox"}):(s=Ze[s])&&s.postMessage({cmd:"checkMailbox"})}var An=[];function Yc(s,c,f,b,w){for(c>>>=0,b/=2,An.length=b,f=w>>>0>>>3,w=0;w<b;w++)An[w]=W[f+2*w]?W[f+2*w+1]:l()[f+2*w+1>>>0];return(c?gn[c]:Np[s])(...An)}function Zc(s){s>>>=0,g?postMessage({cmd:"cleanupThread",thread:s}):Lo(Ze[s])}function Qc(s){}var ir=(s,c)=>{var f=xn[s];if(f===void 0)throw s=Ni(s),f=Qe(s),Je(s),new mt(`${c} has unknown type ${f}`);return f},fi=(s,c,f)=>{var b=[];return s=s.toWireType(b,f),b.length&&(a()[c>>>2>>>0]=We(b)),s};function Xc(s,c,f){return c>>>=0,f>>>=0,s=Re(s>>>0),c=ir(c,"emval::as"),fi(c,f,s)}function Jc(s,c){return c>>>=0,s=Re(s>>>0),(c=ir(c,"emval::as")).toWireType(null,s)}var ar=s=>{try{s()}catch(c){ct(c)}},ht=0,Xe=null,hi=0,sr=[],gi={},bi={},ep=0,kn=null,tp=[];function yi(s){return function(c){if(!De){if(ht===0){var f=!1,b=!1;c((w=0)=>{if(!De&&(hi=w,f=!0,b)){ht=2,ar(()=>ji(Xe)),typeof Browser<"u"&&Browser.Lb.Sb&&Browser.Lb.resume(),w=!1;try{var I=function(){var G=i()[Xe+8>>>2>>>0];return G=Z[bi[G]],--vt,G()}()}catch(G){I=G,w=!0}var O=!1;if(!Xe){var B=kn;B&&(kn=null,(w?B.reject:B.resolve)(I),O=!0)}if(w&&!O)throw I}}),b=!0,f||(ht=1,Xe=function(){var w=mr(65548),I=w+12;a()[w>>>2>>>0]=I,a()[w+4>>>2>>>0]=I+65536,I=sr[0];var O=gi[I];return O===void 0&&(O=ep++,gi[I]=O,bi[O]=I),I=O,i()[w+8>>>2>>>0]=I,w}(),typeof Browser<"u"&&Browser.Lb.Sb&&Browser.Lb.pause(),ar(()=>qi(Xe)))}else ht===2?(ht=0,ar(Yi),Je(Xe),Xe=null,tp.forEach(mi)):ct(`invalid state: ${ht}`);return hi}}(c=>{s().then(c)})}function rp(s){return s>>>=0,yi(()=>(s=Re(s)).then(We))}var ur=[];function np(s,c,f,b){return f>>>=0,b>>>=0,(s=ur[s>>>0])(null,c=Re(c>>>0),f,b)}var op={},dr=s=>{var c=op[s];return c===void 0?Qe(s):c};function ip(s,c,f,b,w){return f>>>=0,b>>>=0,w>>>=0,(s=ur[s>>>0])(c=Re(c>>>0),c[f=dr(f)],b,w)}var _i=()=>typeof globalThis=="object"?globalThis:Function("return this")();function ap(s){return(s>>>=0)==0?We(_i()):(s=dr(s),We(_i()[s]))}var sp=s=>{var c=ur.length;return ur.push(s),c},up=(s,c)=>{for(var f=Array(s),b=0;b<s;++b)f[b]=ir(a()[c+4*b>>>2>>>0],"parameter "+b);return f},wi=(s,c)=>Object.defineProperty(c,"name",{value:s});function dp(s,c,f){var b=(c=up(s,c>>>0)).shift();s--;var w=`return function (obj, func, destructorsRef, args) {
`,I=0,O=[];f===0&&O.push("obj");for(var B=["retType"],G=[b],F=0;F<s;++F)O.push("arg"+F),B.push("argType"+F),G.push(c[F]),w+=`  var arg${F} = argType${F}.readValueFromPointer(args${I?"+"+I:""});
`,I+=c[F].argPackAdvance;return w+=`  var rv = ${f===1?"new func":"func.call"}(${O.join(", ")});
`,b.Ub||(B.push("emval_returnValue"),G.push(fi),w+=`  return emval_returnValue(retType, destructorsRef, rv);
`),B.push(w+`};
`),s=function(X){var le=Function;if(!(le instanceof Function))throw new TypeError(`new_ called with constructor type ${typeof le} which is not a function`);var ge=wi(le.name||"unknownFunctionName",function(){});return ge.prototype=le.prototype,ge=new ge,(X=le.apply(ge,X))instanceof Object?X:ge}(B)(...G),f=`methodCaller<(${c.map(X=>X.name).join(", ")}) => ${b.name}>`,sp(wi(f,s))}function lp(s){return s=dr(s>>>0),We(u[s])}function cp(s,c){return c>>>=0,s=Re(s>>>0),c=Re(c),We(s[c])}function pp(s){9<(s>>>=0)&&(ut[s+1]+=1)}function mp(){return We([])}function fp(s){s=Re(s>>>0);for(var c=Array(s.length),f=0;f<s.length;f++)c[f]=s[f];return We(c)}function hp(s){return We(dr(s>>>0))}function gp(){return We({})}function bp(s){for(var c=Re(s>>>=0);c.length;){var f=c.pop();c.pop()(f)}Tn(s)}function yp(s,c,f){c>>>=0,f>>>=0,s=Re(s>>>0),c=Re(c),f=Re(f),s[c]=f}function _p(s,c){return c>>>=0,s=(s=ir(s>>>0,"_emval_take_value")).readValueFromPointer(c),We(s)}function wp(s,c){s=-9007199254740992>s||9007199254740992<s?NaN:Number(s),c>>>=0,s=new Date(1e3*s),i()[c>>>2>>>0]=s.getUTCSeconds(),i()[c+4>>>2>>>0]=s.getUTCMinutes(),i()[c+8>>>2>>>0]=s.getUTCHours(),i()[c+12>>>2>>>0]=s.getUTCDate(),i()[c+16>>>2>>>0]=s.getUTCMonth(),i()[c+20>>>2>>>0]=s.getUTCFullYear()-1900,i()[c+24>>>2>>>0]=s.getUTCDay(),s=(s.getTime()-Date.UTC(s.getUTCFullYear(),0,1,0,0,0,0))/864e5|0,i()[c+28>>>2>>>0]=s}var Bt=s=>s%4==0&&(s%100!=0||s%400==0),vi=[0,31,60,91,121,152,182,213,244,274,305,335],$i=[0,31,59,90,120,151,181,212,243,273,304,334];function vp(s,c){s=-9007199254740992>s||9007199254740992<s?NaN:Number(s),c>>>=0,s=new Date(1e3*s),i()[c>>>2>>>0]=s.getSeconds(),i()[c+4>>>2>>>0]=s.getMinutes(),i()[c+8>>>2>>>0]=s.getHours(),i()[c+12>>>2>>>0]=s.getDate(),i()[c+16>>>2>>>0]=s.getMonth(),i()[c+20>>>2>>>0]=s.getFullYear()-1900,i()[c+24>>>2>>>0]=s.getDay();var f=(Bt(s.getFullYear())?vi:$i)[s.getMonth()]+s.getDate()-1|0;i()[c+28>>>2>>>0]=f,i()[c+36>>>2>>>0]=-60*s.getTimezoneOffset(),f=new Date(s.getFullYear(),6,1).getTimezoneOffset();var b=new Date(s.getFullYear(),0,1).getTimezoneOffset();s=0|(f!=b&&s.getTimezoneOffset()==Math.min(b,f)),i()[c+32>>>2>>>0]=s}function $p(s){s>>>=0;var c=new Date(i()[s+20>>>2>>>0]+1900,i()[s+16>>>2>>>0],i()[s+12>>>2>>>0],i()[s+8>>>2>>>0],i()[s+4>>>2>>>0],i()[s>>>2>>>0],0),f=i()[s+32>>>2>>>0],b=c.getTimezoneOffset(),w=new Date(c.getFullYear(),6,1).getTimezoneOffset(),I=new Date(c.getFullYear(),0,1).getTimezoneOffset(),O=Math.min(I,w);return 0>f?i()[s+32>>>2>>>0]=+(w!=I&&O==b):0<f!=(O==b)&&(w=Math.max(I,w),c.setTime(c.getTime()+6e4*((0<f?O:w)-b))),i()[s+24>>>2>>>0]=c.getDay(),f=(Bt(c.getFullYear())?vi:$i)[c.getMonth()]+c.getDate()-1|0,i()[s+28>>>2>>>0]=f,i()[s>>>2>>>0]=c.getSeconds(),i()[s+4>>>2>>>0]=c.getMinutes(),i()[s+8>>>2>>>0]=c.getHours(),i()[s+12>>>2>>>0]=c.getDate(),i()[s+16>>>2>>>0]=c.getMonth(),i()[s+20>>>2>>>0]=c.getYear(),s=c.getTime(),BigInt(isNaN(s)?-1:s/1e3)}function xi(s,c,f,b,w,I,O){return g?$e(16,1,s,c,f,b,w,I,O):-52}function Si(s,c,f,b,w,I){if(g)return $e(17,1,s,c,f,b,w,I)}function xp(s,c,f,b){s>>>=0,c>>>=0,f>>>=0,b>>>=0;var w=new Date().getFullYear(),I=new Date(w,0,1),O=new Date(w,6,1);w=I.getTimezoneOffset();var B=O.getTimezoneOffset(),G=Math.max(w,B);a()[s>>>2>>>0]=60*G,i()[c>>>2>>>0]=+(w!=B),I=(s=F=>F.toLocaleTimeString(void 0,{hour12:!1,timeZoneName:"short"}).split(" ")[1])(I),O=s(O),B<w?(Dt(I,f,17),Dt(O,b,17)):(Dt(I,b,17),Dt(O,f,17))}var En=[],Ti=(s,c)=>{En.length=0;for(var f;f=r()[s++>>>0];){var b=f!=105;c+=(b&=f!=112)&&c%8?4:0,En.push(f==112?a()[c>>>2>>>0]:f==106?W[c>>>3]:f==105?i()[c>>>2>>>0]:l()[c>>>3>>>0]),c+=b?8:4}return En};function Sp(s,c,f){return s>>>=0,c=Ti(c>>>0,f>>>0),gn[s](...c)}function Tp(s,c,f){return s>>>=0,c=Ti(c>>>0,f>>>0),gn[s](...c)}var Ip=()=>{},Cp=()=>Date.now();function Ap(s,c){return L(Ce(s>>>0,c>>>0))}var Ii,kp=()=>{throw vt+=1,"unwind"};function Ep(){return 4294901760}Ii=()=>performance.timeOrigin+performance.now();var Pp=()=>navigator.hardwareConcurrency;function zp(){return ct("Cannot use emscripten_pc_get_function without -sUSE_OFFSET_CONVERTER"),0}function Op(s){s>>>=0;var c=r().length;if(s<=c||4294901760<s)return!1;for(var f=1;4>=f;f*=2){var b=c*(1+.2/f);b=Math.min(b,s+100663296);var w=Math;b=Math.max(s,b);e:{w=(w.min.call(w,4294901760,b+(65536-b%65536)%65536)-K.buffer.byteLength+65535)/65536;try{K.grow(w),pe();var I=1;break e}catch{}I=void 0}if(I)return!0}return!1}var lr=()=>(ct("Cannot use convertFrameToPC (needed by __builtin_return_address) without -sUSE_OFFSET_CONVERTER"),0),Mt={},Ci=s=>{s.forEach(c=>{var f=lr();f&&(Mt[f]=c)})};function Dp(){var s=Error().stack.toString().split(`
`);return s[0]=="Error"&&s.shift(),Ci(s),Mt.Qb=lr(),Mt.fc=s,Mt.Qb}function Bp(s,c,f){if(s>>>=0,c>>>=0,Mt.Qb==s)var b=Mt.fc;else(b=Error().stack.toString().split(`
`))[0]=="Error"&&b.shift(),Ci(b);for(var w=3;b[w]&&lr()!=s;)++w;for(s=0;s<f&&b[s+w];++s)i()[c+4*s>>>2>>>0]=lr();return s}var Pn,zn={},Ai=()=>{if(!Pn){var s,c={USER:"web_user",LOGNAME:"web_user",PATH:"/",PWD:"/",HOME:"/home/web_user",LANG:(typeof navigator=="object"&&navigator.languages&&navigator.languages[0]||"C").replace("-","_")+".UTF-8",_:"./this.program"};for(s in zn)zn[s]===void 0?delete c[s]:c[s]=zn[s];var f=[];for(s in c)f.push(`${s}=${c[s]}`);Pn=f}return Pn};function ki(s,c){if(g)return $e(18,1,s,c);s>>>=0,c>>>=0;var f=0;return Ai().forEach((b,w)=>{var I=c+f;for(w=a()[s+4*w>>>2>>>0]=I,I=0;I<b.length;++I)t()[w++>>>0]=b.charCodeAt(I);t()[w>>>0]=0,f+=b.length+1}),0}function Ei(s,c){if(g)return $e(19,1,s,c);s>>>=0,c>>>=0;var f=Ai();a()[s>>>2>>>0]=f.length;var b=0;return f.forEach(w=>b+=w.length+1),a()[c>>>2>>>0]=b,0}function Pi(s){return g?$e(20,1,s):52}function zi(s,c,f,b){return g?$e(21,1,s,c,f,b):52}function Oi(s,c,f,b){return g?$e(22,1,s,c,f,b):70}var Mp=[null,[],[]];function Di(s,c,f,b){if(g)return $e(23,1,s,c,f,b);c>>>=0,f>>>=0,b>>>=0;for(var w=0,I=0;I<f;I++){var O=a()[c>>>2>>>0],B=a()[c+4>>>2>>>0];c+=8;for(var G=0;G<B;G++){var F=r()[O+G>>>0],X=Mp[s];F===0||F===10?((s===1?H:L)(Yo(X,0)),X.length=0):X.push(F)}w+=B}return a()[b>>>2>>>0]=w,0}var Bi=[31,29,31,30,31,30,31,31,30,31,30,31],Mi=[31,28,31,30,31,30,31,31,30,31,30,31],Rp=(s,c)=>{t().set(s,c>>>0)};function Ri(s,c,f,b){function w(z,ue,Se){for(z=typeof z=="number"?z.toString():z||"";z.length<ue;)z=Se[0]+z;return z}function I(z,ue){return w(z,ue,"0")}function O(z,ue){function Se(Qi){return 0>Qi?-1:0<Qi?1:0}var xt;return(xt=Se(z.getFullYear()-ue.getFullYear()))===0&&(xt=Se(z.getMonth()-ue.getMonth()))===0&&(xt=Se(z.getDate()-ue.getDate())),xt}function B(z){switch(z.getDay()){case 0:return new Date(z.getFullYear()-1,11,29);case 1:return z;case 2:return new Date(z.getFullYear(),0,3);case 3:return new Date(z.getFullYear(),0,2);case 4:return new Date(z.getFullYear(),0,1);case 5:return new Date(z.getFullYear()-1,11,31);case 6:return new Date(z.getFullYear()-1,11,30)}}function G(z){var ue=z.Cb;for(z=new Date(new Date(z.Db+1900,0,1).getTime());0<ue;){var Se=z.getMonth(),xt=(Bt(z.getFullYear())?Bi:Mi)[Se];if(!(ue>xt-z.getDate())){z.setDate(z.getDate()+ue);break}ue-=xt-z.getDate()+1,z.setDate(1),11>Se?z.setMonth(Se+1):(z.setMonth(0),z.setFullYear(z.getFullYear()+1))}return Se=new Date(z.getFullYear()+1,0,4),ue=B(new Date(z.getFullYear(),0,4)),Se=B(Se),0>=O(ue,z)?0>=O(Se,z)?z.getFullYear()+1:z.getFullYear():z.getFullYear()-1}s>>>=0,c>>>=0,f>>>=0,b>>>=0;var F=a()[b+40>>>2>>>0];for(var X in b={lc:i()[b>>>2>>>0],kc:i()[b+4>>>2>>>0],Ib:i()[b+8>>>2>>>0],Mb:i()[b+12>>>2>>>0],Jb:i()[b+16>>>2>>>0],Db:i()[b+20>>>2>>>0],vb:i()[b+24>>>2>>>0],Cb:i()[b+28>>>2>>>0],sc:i()[b+32>>>2>>>0],jc:i()[b+36>>>2>>>0],mc:F?Ce(F):""},f=Ce(f),F={"%c":"%a %b %d %H:%M:%S %Y","%D":"%m/%d/%y","%F":"%Y-%m-%d","%h":"%b","%r":"%I:%M:%S %p","%R":"%H:%M","%T":"%H:%M:%S","%x":"%m/%d/%y","%X":"%H:%M:%S","%Ec":"%c","%EC":"%C","%Ex":"%m/%d/%y","%EX":"%H:%M:%S","%Ey":"%y","%EY":"%Y","%Od":"%d","%Oe":"%e","%OH":"%H","%OI":"%I","%Om":"%m","%OM":"%M","%OS":"%S","%Ou":"%u","%OU":"%U","%OV":"%V","%Ow":"%w","%OW":"%W","%Oy":"%y"})f=f.replace(new RegExp(X,"g"),F[X]);var le="Sunday Monday Tuesday Wednesday Thursday Friday Saturday".split(" "),ge="January February March April May June July August September October November December".split(" ");for(X in F={"%a":z=>le[z.vb].substring(0,3),"%A":z=>le[z.vb],"%b":z=>ge[z.Jb].substring(0,3),"%B":z=>ge[z.Jb],"%C":z=>I((z.Db+1900)/100|0,2),"%d":z=>I(z.Mb,2),"%e":z=>w(z.Mb,2," "),"%g":z=>G(z).toString().substring(2),"%G":G,"%H":z=>I(z.Ib,2),"%I":z=>((z=z.Ib)==0?z=12:12<z&&(z-=12),I(z,2)),"%j":z=>{for(var ue=0,Se=0;Se<=z.Jb-1;ue+=(Bt(z.Db+1900)?Bi:Mi)[Se++]);return I(z.Mb+ue,3)},"%m":z=>I(z.Jb+1,2),"%M":z=>I(z.kc,2),"%n":()=>`
`,"%p":z=>0<=z.Ib&&12>z.Ib?"AM":"PM","%S":z=>I(z.lc,2),"%t":()=>"	","%u":z=>z.vb||7,"%U":z=>I(Math.floor((z.Cb+7-z.vb)/7),2),"%V":z=>{var ue=Math.floor((z.Cb+7-(z.vb+6)%7)/7);if(2>=(z.vb+371-z.Cb-2)%7&&ue++,ue)ue==53&&((Se=(z.vb+371-z.Cb)%7)==4||Se==3&&Bt(z.Db)||(ue=1));else{ue=52;var Se=(z.vb+7-z.Cb-1)%7;(Se==4||Se==5&&Bt(z.Db%400-1))&&ue++}return I(ue,2)},"%w":z=>z.vb,"%W":z=>I(Math.floor((z.Cb+7-(z.vb+6)%7)/7),2),"%y":z=>(z.Db+1900).toString().substring(2),"%Y":z=>z.Db+1900,"%z":z=>{var ue=0<=(z=z.jc);return z=Math.abs(z)/60,(ue?"+":"-")+("0000"+(z/60*100+z%60)).slice(-4)},"%Z":z=>z.mc,"%%":()=>"%"},f=f.replace(/%%/g,"\0\0"),F)f.includes(X)&&(f=f.replace(new RegExp(X,"g"),F[X](b)));return X=function(z){var ue=Array(vn(z)+1);return Xo(z,ue,0,ue.length),ue}(f=f.replace(/\0\0/g,"%")),X.length>c?0:(Rp(X,s),X.length-1)}function Up(s,c,f,b){return Ri(s>>>0,c>>>0,f>>>0,b>>>0)}g||function(){for(var s=u.numThreads-1;s--;)Fo();Ie.unshift(()=>{wt++,function(c){g?c():Promise.all(pt.map(Ho)).then(c)}(()=>Oo())})}();for(var Ui=Array(256),cr=0;256>cr;++cr)Ui[cr]=String.fromCharCode(cr);li=Ui,mt=u.BindingError=class extends Error{constructor(s){super(s),this.name="BindingError"}},u.InternalError=class extends Error{constructor(s){super(s),this.name="InternalError"}},ut.push(0,1,void 0,1,null,1,!0,1,!1,1),u.count_emval_handles=()=>ut.length/2-5-Sn.length;var Np=[_n,Vo,qo,Zo,Qo,Jo,ei,ti,ri,ni,oi,ii,ai,si,ui,di,xi,Si,ki,Ei,Pi,zi,Oi,Di],Z=function(){function s(f,b){return Z=f.exports,Z=function(){var w=Z,I={};for(let[O,B]of Object.entries(w))I[O]=typeof B=="function"?(...G)=>{sr.push(O);try{return B(...G)}finally{De||(sr.pop(),Xe&&ht===1&&sr.length===0&&(ht=0,vt+=1,ar(Ki),typeof Fibers<"u"&&Fibers.tc()))}}:B;return I}(),Z=function(){var w=Z,I=B=>G=>B(G)>>>0,O=B=>()=>B()>>>0;return(w=Object.assign({},w)).Da=I(w.Da),w.gb=O(w.gb),w.ib=I(w.ib),w.emscripten_main_runtime_thread_id=O(w.emscripten_main_runtime_thread_id),w.tb=I(w.tb),w.ub=O(w.ub),w}(),Wo.push(Z.jb),He.unshift(Z.Ca),we=b,Oo(),Z}var c=Uo();if(wt++,u.instantiateWasm)try{return u.instantiateWasm(c,s)}catch(f){L(`Module.instantiateWasm callback failed with error: ${f}`),m(f)}return hn||=u.locateFile?Do("ort-wasm-simd-threaded.jsep.wasm")?"ort-wasm-simd-threaded.jsep.wasm":u.locateFile?u.locateFile("ort-wasm-simd-threaded.jsep.wasm",C):C+"ort-wasm-simd-threaded.jsep.wasm":new URL("ort-wasm-simd-threaded.jsep.wasm",import.meta.url).href,function(f,b){var w=hn;return P||typeof WebAssembly.instantiateStreaming!="function"||Do(w)||Bo(w)||typeof fetch!="function"?Ro(w,f,b):fetch(w,{credentials:"same-origin"}).then(I=>WebAssembly.instantiateStreaming(I,f).then(b,function(O){return L(`wasm streaming compile failed: ${O}`),L("falling back to ArrayBuffer instantiation"),Ro(w,f,b)}))}(c,function(f){s(f.instance,f.module)}).catch(m),{}}(),Ni=s=>(Ni=Z.Da)(s),Vi=()=>(Vi=Z.Ea)();u._OrtInit=(s,c)=>(u._OrtInit=Z.Fa)(s,c),u._OrtGetLastError=(s,c)=>(u._OrtGetLastError=Z.Ga)(s,c),u._OrtCreateSessionOptions=(s,c,f,b,w,I,O,B,G,F)=>(u._OrtCreateSessionOptions=Z.Ha)(s,c,f,b,w,I,O,B,G,F),u._OrtAppendExecutionProvider=(s,c)=>(u._OrtAppendExecutionProvider=Z.Ia)(s,c),u._OrtAddFreeDimensionOverride=(s,c,f)=>(u._OrtAddFreeDimensionOverride=Z.Ja)(s,c,f),u._OrtAddSessionConfigEntry=(s,c,f)=>(u._OrtAddSessionConfigEntry=Z.Ka)(s,c,f),u._OrtReleaseSessionOptions=s=>(u._OrtReleaseSessionOptions=Z.La)(s),u._OrtCreateSession=(s,c,f)=>(u._OrtCreateSession=Z.Ma)(s,c,f),u._OrtReleaseSession=s=>(u._OrtReleaseSession=Z.Na)(s),u._OrtGetInputOutputCount=(s,c,f)=>(u._OrtGetInputOutputCount=Z.Oa)(s,c,f),u._OrtGetInputName=(s,c)=>(u._OrtGetInputName=Z.Pa)(s,c),u._OrtGetOutputName=(s,c)=>(u._OrtGetOutputName=Z.Qa)(s,c),u._OrtFree=s=>(u._OrtFree=Z.Ra)(s),u._OrtCreateTensor=(s,c,f,b,w,I)=>(u._OrtCreateTensor=Z.Sa)(s,c,f,b,w,I),u._OrtGetTensorData=(s,c,f,b,w)=>(u._OrtGetTensorData=Z.Ta)(s,c,f,b,w),u._OrtReleaseTensor=s=>(u._OrtReleaseTensor=Z.Ua)(s),u._OrtCreateRunOptions=(s,c,f,b)=>(u._OrtCreateRunOptions=Z.Va)(s,c,f,b),u._OrtAddRunConfigEntry=(s,c,f)=>(u._OrtAddRunConfigEntry=Z.Wa)(s,c,f),u._OrtReleaseRunOptions=s=>(u._OrtReleaseRunOptions=Z.Xa)(s),u._OrtCreateBinding=s=>(u._OrtCreateBinding=Z.Ya)(s),u._OrtBindInput=(s,c,f)=>(u._OrtBindInput=Z.Za)(s,c,f),u._OrtBindOutput=(s,c,f,b)=>(u._OrtBindOutput=Z._a)(s,c,f,b),u._OrtClearBoundOutputs=s=>(u._OrtClearBoundOutputs=Z.$a)(s),u._OrtReleaseBinding=s=>(u._OrtReleaseBinding=Z.ab)(s),u._OrtRunWithBinding=(s,c,f,b,w)=>(u._OrtRunWithBinding=Z.bb)(s,c,f,b,w),u._OrtRun=(s,c,f,b,w,I,O,B)=>(u._OrtRun=Z.cb)(s,c,f,b,w,I,O,B),u._OrtEndProfiling=s=>(u._OrtEndProfiling=Z.db)(s),u._JsepOutput=(s,c,f)=>(u._JsepOutput=Z.eb)(s,c,f),u._JsepGetNodeName=s=>(u._JsepGetNodeName=Z.fb)(s);var pr,Rt=()=>(Rt=Z.gb)(),Je=u._free=s=>(Je=u._free=Z.hb)(s),mr=u._malloc=s=>(mr=u._malloc=Z.ib)(s),On=(s,c,f,b,w,I)=>(On=Z.lb)(s,c,f,b,w,I),Wi=()=>(Wi=Z.mb)(),Li=(s,c,f,b,w)=>(Li=Z.nb)(s,c,f,b,w),Dn=s=>(Dn=Z.ob)(s),fr=s=>(fr=Z.pb)(s),Gi=()=>(Gi=Z.qb)(),Hi=(s,c)=>(Hi=Z.rb)(s,c),hr=s=>(hr=Z.sb)(s),Bn=s=>(Bn=Z.tb)(s),Mn=()=>(Mn=Z.ub)(),Fi=u.dynCall_ii=(s,c)=>(Fi=u.dynCall_ii=Z.wb)(s,c),qi=s=>(qi=Z.xb)(s),Ki=()=>(Ki=Z.yb)(),ji=s=>(ji=Z.zb)(s),Yi=()=>(Yi=Z.Ab)();function Zi(){0<wt||(g?(p(u),g||nr(He),startWorker(u)):(nr(Ie),0<wt||pr||(pr=!0,u.calledRun=!0,De||(g||nr(He),p(u),g||nr(mn)))))}return u.___start_em_js=932469,u.___stop_em_js=932715,u.stackSave=()=>Mn(),u.stackRestore=s=>hr(s),u.stackAlloc=s=>Bn(s),u.setValue=function(s,c,f="i8"){switch(f.endsWith("*")&&(f="*"),f){case"i1":case"i8":t()[s>>>0]=c;break;case"i16":n()[s>>>1>>>0]=c;break;case"i32":i()[s>>>2>>>0]=c;break;case"i64":W[s>>>3]=BigInt(c);break;case"float":d()[s>>>2>>>0]=c;break;case"double":l()[s>>>3>>>0]=c;break;case"*":a()[s>>>2>>>0]=c;break;default:ct(`invalid type for setValue: ${f}`)}},u.getValue=function(s,c="i8"){switch(c.endsWith("*")&&(c="*"),c){case"i1":case"i8":return t()[s>>>0];case"i16":return n()[s>>>1>>>0];case"i32":return i()[s>>>2>>>0];case"i64":return W[s>>>3];case"float":return d()[s>>>2>>>0];case"double":return l()[s>>>3>>>0];case"*":return a()[s>>>2>>>0];default:ct(`invalid type for getValue: ${c}`)}},u.UTF8ToString=Ce,u.stringToUTF8=Dt,u.lengthBytesUTF8=vn,Gt=function s(){pr||Zi(),pr||(Gt=s)},Zi(),u.PTR_SIZE=4,h}),Kp=Pa;globalThis.self?.name==="em-pthread"&&Pa()});var Ma,jp,Ve,Ra,Kn,Yp,Zp,Ua,Qp,Da,Na,Ba,Va,$r=U(()=>{"use strict";vr();Ma=!1||typeof location>"u"?void 0:location.origin,jp=()=>{if(!!1)return import.meta.url?.startsWith("file:")?new URL(new URL("ort.bundle.min.mjs",import.meta.url).href,Ma).href:import.meta.url},Ve=jp(),Ra=()=>{if(Ve&&!Ve.startsWith("blob:"))return Ve.substring(0,Ve.lastIndexOf("/")+1)},Kn=(e,t)=>{try{let r=t??Ve;return(r?new URL(e,r):new URL(e)).origin===Ma}catch{return!1}},Yp=(e,t)=>{let r=t??Ve;try{return(r?new URL(e,r):new URL(e)).href}catch{return}},Zp=(e,t)=>`${t??"./"}${e}`,Ua=async e=>{let r=await(await fetch(e,{credentials:"same-origin"})).blob();return URL.createObjectURL(r)},Qp=async e=>(await import(/*webpackIgnore:true*/e)).default,Da=(Ea(),gr(ka)).default,Na=async()=>{if(!Ve)throw new Error("Failed to load proxy worker: cannot determine the script source URL.");if(Kn(Ve))return[void 0,Da()];let e=await Ua(Ve);return[e,Da(e)]},Ba=(Oa(),gr(za)).default,Va=async(e,t,r)=>{if(!e&&!t&&Ba&&Ve&&Kn(Ve))return[void 0,Ba];{let n="ort-wasm-simd-threaded.jsep.mjs",o=e??Yp(n,t),i=!!1&&r&&o&&!Kn(o,t),a=i?await Ua(o):o??Zp(n,t);return[i?a:void 0,await Qp(a)]}}});var jn,Yn,Pr,Wa,Xp,Jp,xr,Te,gt=U(()=>{"use strict";$r();Yn=!1,Pr=!1,Wa=!1,Xp=()=>{if(typeof SharedArrayBuffer>"u")return!1;try{return typeof MessageChannel<"u"&&new MessageChannel().port1.postMessage(new SharedArrayBuffer(1)),WebAssembly.validate(new Uint8Array([0,97,115,109,1,0,0,0,1,4,1,96,0,0,3,2,1,0,5,4,1,3,1,1,10,11,1,9,0,65,0,254,16,2,0,26,11]))}catch{return!1}},Jp=()=>{try{return WebAssembly.validate(new Uint8Array([0,97,115,109,1,0,0,0,1,4,1,96,0,0,3,2,1,0,10,30,1,28,0,65,0,253,15,253,12,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,253,186,1,26,11]))}catch{return!1}},xr=async e=>{if(Yn)return Promise.resolve();if(Pr)throw new Error("multiple calls to 'initializeWebAssembly()' detected.");if(Wa)throw new Error("previous call to 'initializeWebAssembly()' failed.");Pr=!0;let t=e.initTimeout,r=e.numThreads;if(!Jp())throw new Error("WebAssembly SIMD is not supported in the current environment.");let n=Xp();r>1&&!n&&(typeof self<"u"&&!self.crossOriginIsolated&&console.warn("env.wasm.numThreads is set to "+r+", but this will not work unless you enable crossOriginIsolated mode. See https://web.dev/cross-origin-isolation-guide/ for more info."),console.warn("WebAssembly multi-threading is not supported in the current environment. Falling back to single-threading."),e.numThreads=r=1);let o=e.wasmPaths,i=typeof o=="string"?o:void 0,a=o?.mjs,d=a?.href??a,l=o?.wasm,p=l?.href??l,m=e.wasmBinary,[u,h]=await Va(d,i,r>1),_=!1,y=[];if(t>0&&y.push(new Promise(g=>{setTimeout(()=>{_=!0,g()},t)})),y.push(new Promise((g,x)=>{let $={numThreads:r};if(m)$.wasmBinary=m;else if(p||i)$.locateFile=v=>p??i+v;else if(d&&d.indexOf("blob:")!==0)$.locateFile=v=>new URL(v,d).href;else if(u){let v=Ra();v&&($.locateFile=S=>v+S)}h($).then(v=>{Pr=!1,Yn=!0,jn=v,g(),u&&URL.revokeObjectURL(u)},v=>{Pr=!1,Wa=!0,x(v)})})),await Promise.race(y),_)throw new Error(`WebAssembly backend initializing failed due to timeout: ${t}ms`)},Te=()=>{if(Yn&&jn)return jn;throw new Error("WebAssembly is not initialized yet.")}});var ke,Kt,ce,zr=U(()=>{"use strict";gt();ke=(e,t)=>{let r=Te(),n=r.lengthBytesUTF8(e)+1,o=r._malloc(n);return r.stringToUTF8(e,o,n),t.push(o),o},Kt=(e,t,r,n)=>{if(typeof e=="object"&&e!==null){if(r.has(e))throw new Error("Circular reference in options");r.add(e)}Object.entries(e).forEach(([o,i])=>{let a=t?t+o:o;if(typeof i=="object")Kt(i,a+".",r,n);else if(typeof i=="string"||typeof i=="number")n(a,i.toString());else if(typeof i=="boolean")n(a,i?"1":"0");else throw new Error(`Can't handle extra config type: ${typeof i}`)})},ce=e=>{let t=Te(),r=t.stackSave();try{let n=t.PTR_SIZE,o=t.stackAlloc(2*n);t._OrtGetLastError(o,o+n);let i=Number(t.getValue(o,n===4?"i32":"i64")),a=t.getValue(o+n,"*"),d=a?t.UTF8ToString(a):"";throw new Error(`${e} ERROR_CODE: ${i}, ERROR_MESSAGE: ${d}`)}finally{t.stackRestore(r)}}});var La,Ga=U(()=>{"use strict";gt();zr();La=e=>{let t=Te(),r=0,n=[],o=e||{};try{if(e?.logSeverityLevel===void 0)o.logSeverityLevel=2;else if(typeof e.logSeverityLevel!="number"||!Number.isInteger(e.logSeverityLevel)||e.logSeverityLevel<0||e.logSeverityLevel>4)throw new Error(`log serverity level is not valid: ${e.logSeverityLevel}`);if(e?.logVerbosityLevel===void 0)o.logVerbosityLevel=0;else if(typeof e.logVerbosityLevel!="number"||!Number.isInteger(e.logVerbosityLevel))throw new Error(`log verbosity level is not valid: ${e.logVerbosityLevel}`);e?.terminate===void 0&&(o.terminate=!1);let i=0;return e?.tag!==void 0&&(i=ke(e.tag,n)),r=t._OrtCreateRunOptions(o.logSeverityLevel,o.logVerbosityLevel,!!o.terminate,i),r===0&&ce("Can't create run options."),e?.extra!==void 0&&Kt(e.extra,"",new WeakSet,(a,d)=>{let l=ke(a,n),p=ke(d,n);t._OrtAddRunConfigEntry(r,l,p)!==0&&ce(`Can't set a run config entry: ${a} - ${d}.`)}),[r,n]}catch(i){throw r!==0&&t._OrtReleaseRunOptions(r),n.forEach(a=>t._free(a)),i}}});var em,tm,rm,nm,Ha,Fa=U(()=>{"use strict";gt();zr();em=e=>{switch(e){case"disabled":return 0;case"basic":return 1;case"extended":return 2;case"all":return 99;default:throw new Error(`unsupported graph optimization level: ${e}`)}},tm=e=>{switch(e){case"sequential":return 0;case"parallel":return 1;default:throw new Error(`unsupported execution mode: ${e}`)}},rm=e=>{e.extra||(e.extra={}),e.extra.session||(e.extra.session={});let t=e.extra.session;t.use_ort_model_bytes_directly||(t.use_ort_model_bytes_directly="1"),e.executionProviders&&e.executionProviders.some(r=>(typeof r=="string"?r:r.name)==="webgpu")&&(e.enableMemPattern=!1)},nm=(e,t,r)=>{for(let n of t){let o=typeof n=="string"?n:n.name;switch(o){case"webnn":if(o="WEBNN",typeof n!="string"){let d=n?.deviceType;if(d){let l=ke("deviceType",r),p=ke(d,r);Te()._OrtAddSessionConfigEntry(e,l,p)!==0&&ce(`Can't set a session config entry: 'deviceType' - ${d}.`)}}break;case"webgpu":if(o="JS",typeof n!="string"){let a=n;if(a?.preferredLayout){if(a.preferredLayout!=="NCHW"&&a.preferredLayout!=="NHWC")throw new Error(`preferredLayout must be either 'NCHW' or 'NHWC': ${a.preferredLayout}`);let d=ke("preferredLayout",r),l=ke(a.preferredLayout,r);Te()._OrtAddSessionConfigEntry(e,d,l)!==0&&ce(`Can't set a session config entry: 'preferredLayout' - ${a.preferredLayout}.`)}}break;case"wasm":case"cpu":continue;default:throw new Error(`not supported execution provider: ${o}`)}let i=ke(o,r);Te()._OrtAppendExecutionProvider(e,i)!==0&&ce(`Can't append execution provider: ${o}.`)}},Ha=e=>{let t=Te(),r=0,n=[],o=e||{};rm(o);try{let i=em(o.graphOptimizationLevel??"all"),a=tm(o.executionMode??"sequential"),d=typeof o.logId=="string"?ke(o.logId,n):0,l=o.logSeverityLevel??2;if(!Number.isInteger(l)||l<0||l>4)throw new Error(`log serverity level is not valid: ${l}`);let p=o.logVerbosityLevel??0;if(!Number.isInteger(p)||p<0||p>4)throw new Error(`log verbosity level is not valid: ${p}`);let m=typeof o.optimizedModelFilePath=="string"?ke(o.optimizedModelFilePath,n):0;if(r=t._OrtCreateSessionOptions(i,!!o.enableCpuMemArena,!!o.enableMemPattern,a,!!o.enableProfiling,0,d,l,p,m),r===0&&ce("Can't create session options."),o.executionProviders&&nm(r,o.executionProviders,n),o.enableGraphCapture!==void 0){if(typeof o.enableGraphCapture!="boolean")throw new Error(`enableGraphCapture must be a boolean value: ${o.enableGraphCapture}`);let u=ke("enableGraphCapture",n),h=ke(o.enableGraphCapture.toString(),n);t._OrtAddSessionConfigEntry(r,u,h)!==0&&ce(`Can't set a session config entry: 'enableGraphCapture' - ${o.enableGraphCapture}.`)}if(o.freeDimensionOverrides)for(let[u,h]of Object.entries(o.freeDimensionOverrides)){if(typeof u!="string")throw new Error(`free dimension override name must be a string: ${u}`);if(typeof h!="number"||!Number.isInteger(h)||h<0)throw new Error(`free dimension override value must be a non-negative integer: ${h}`);let _=ke(u,n);t._OrtAddFreeDimensionOverride(r,_,h)!==0&&ce(`Can't set a free dimension override: ${u} - ${h}.`)}return o.extra!==void 0&&Kt(o.extra,"",new WeakSet,(u,h)=>{let _=ke(u,n),y=ke(h,n);t._OrtAddSessionConfigEntry(r,_,y)!==0&&ce(`Can't set a session config entry: ${u} - ${h}.`)}),[r,n]}catch(i){throw r!==0&&t._OrtReleaseSessionOptions(r)!==0&&ce("Can't release session options."),n.forEach(a=>t._free(a)),i}}});var jt,bt,At,Or,Yt,Dr,Br,Zn,J=U(()=>{"use strict";jt=e=>{switch(e){case"int8":return 3;case"uint8":return 2;case"bool":return 9;case"int16":return 5;case"uint16":return 4;case"int32":return 6;case"uint32":return 12;case"float16":return 10;case"float32":return 1;case"float64":return 11;case"string":return 8;case"int64":return 7;case"uint64":return 13;case"int4":return 22;case"uint4":return 21;default:throw new Error(`unsupported data type: ${e}`)}},bt=e=>{switch(e){case 3:return"int8";case 2:return"uint8";case 9:return"bool";case 5:return"int16";case 4:return"uint16";case 6:return"int32";case 12:return"uint32";case 10:return"float16";case 1:return"float32";case 11:return"float64";case 8:return"string";case 7:return"int64";case 13:return"uint64";case 22:return"int4";case 21:return"uint4";default:throw new Error(`unsupported data type: ${e}`)}},At=(e,t)=>{let r=[-1,4,1,1,2,2,4,8,-1,1,2,8,4,8,-1,-1,-1,-1,-1,-1,-1,.5,.5][e],n=typeof t=="number"?t:t.reduce((o,i)=>o*i,1);return r>0?Math.ceil(n*r):void 0},Or=e=>{switch(e){case"float16":return typeof Float16Array<"u"&&Float16Array.from?Float16Array:Uint16Array;case"float32":return Float32Array;case"uint8":return Uint8Array;case"int8":return Int8Array;case"uint16":return Uint16Array;case"int16":return Int16Array;case"int32":return Int32Array;case"bool":return Uint8Array;case"float64":return Float64Array;case"uint32":return Uint32Array;case"int64":return BigInt64Array;case"uint64":return BigUint64Array;default:throw new Error(`unsupported type: ${e}`)}},Yt=e=>{switch(e){case"verbose":return 0;case"info":return 1;case"warning":return 2;case"error":return 3;case"fatal":return 4;default:throw new Error(`unsupported logging level: ${e}`)}},Dr=e=>e==="float32"||e==="float16"||e==="int32"||e==="int64"||e==="uint32"||e==="uint8"||e==="bool"||e==="uint4"||e==="int4",Br=e=>e==="float32"||e==="float16"||e==="int32"||e==="int64"||e==="uint32"||e==="uint64"||e==="int8"||e==="uint8"||e==="bool"||e==="uint4"||e==="int4",Zn=e=>{switch(e){case"none":return 0;case"cpu":return 1;case"cpu-pinned":return 2;case"texture":return 3;case"gpu-buffer":return 4;case"ml-tensor":return 5;default:throw new Error(`unsupported data location: ${e}`)}}});var Zt,Qn=U(()=>{"use strict";vr();Zt=async e=>{if(typeof e=="string")if(!1)try{let{readFile:t}=Un("node:fs/promises");return new Uint8Array(await t(e))}catch(t){if(t.code==="ERR_FS_FILE_TOO_LARGE"){let{createReadStream:r}=Un("node:fs"),n=r(e),o=[];for await(let i of n)o.push(i);return new Uint8Array(Buffer.concat(o))}throw t}else{let t=await fetch(e);if(!t.ok)throw new Error(`failed to load external data file: ${e}`);let r=t.headers.get("Content-Length"),n=r?parseInt(r,10):0;if(n<1073741824)return new Uint8Array(await t.arrayBuffer());{if(!t.body)throw new Error(`failed to load external data file: ${e}, no response body.`);let o=t.body.getReader(),i;try{i=new ArrayBuffer(n)}catch(d){if(d instanceof RangeError){let l=Math.ceil(n/65536);i=new WebAssembly.Memory({initial:l,maximum:l}).buffer}else throw d}let a=0;for(;;){let{done:d,value:l}=await o.read();if(d)break;let p=l.byteLength;new Uint8Array(i,a,p).set(l),a+=p}return new Uint8Array(i,0,n)}}else return e instanceof Blob?new Uint8Array(await e.arrayBuffer()):e instanceof Uint8Array?e:new Uint8Array(e)}});var om,im,qa,Ka,Mr,am,se,et=U(()=>{"use strict";J();om=["V","I","W","E","F"],im=(e,t)=>{console.log(`[${om[e]},${new Date().toISOString()}]${t}`)},Mr=(e,t)=>{qa=e,Ka=t},am=(e,t)=>{let r=Yt(e),n=Yt(qa);r>=n&&im(r,typeof t=="function"?t():t)},se=(...e)=>{Ka&&am(...e)}});var Rr,Xn=U(()=>{"use strict";J();Rr=(e,t)=>new(Or(t))(e)});var Ur=U(()=>{"use strict"});var ja,Jn,eo,sm,um,Ya,ro,to,Qa,Xa=U(()=>{"use strict";et();Ur();ja=new Map([[64,250],[128,200],[256,200],[512,200],[2048,230],[4096,200],[8192,50],[16384,50],[32768,50],[65536,50],[131072,50],[262144,50],[524288,50],[1048576,50],[2097152,30],[4194304,20],[8388608,10],[12582912,10],[16777216,10],[26214400,15],[33554432,22],[44236800,2],[58982400,6],[67108864,6],[134217728,6],[167772160,6]]),Jn=[],eo=e=>Math.ceil(Number(e)/16)*16,sm=e=>{for(let t=0;t<Jn.length;t++){let r=Jn[t];if(e<=r)return r}return Math.ceil(e/16)*16},um=1,Ya=()=>um++,ro=async(e,t,r,n)=>{let o=eo(r),i=e.device.createBuffer({size:o,usage:GPUBufferUsage.COPY_DST|GPUBufferUsage.MAP_READ});try{let a=e.getCommandEncoder();e.endComputePass(),a.copyBufferToBuffer(t,0,i,0,o),e.flush(),await i.mapAsync(GPUMapMode.READ);let d=i.getMappedRange();if(n){let l=n();return l.set(new Uint8Array(d,0,r)),l}else return new Uint8Array(d.slice(0,r))}finally{i.destroy()}},to=class{constructor(t){this.backend=t;this.storageCache=new Map,this.freeBuffers=new Map,this.freeUniformBuffers=new Map,this.buffersPending=[],this.capturedPendingBuffers=new Map;for(let[r]of ja)Jn.push(r),this.freeBuffers.set(r,[]),this.freeUniformBuffers.set(r,[]);this.sessionCount=0}upload(t,r){let n=r.buffer,o=r.byteOffset,i=r.byteLength,a=eo(i),d=this.storageCache.get(t);if(!d)throw new Error("gpu data for uploading does not exist");if(Number(d.originalSize)!==i)throw new Error(`inconsistent data size. gpu data size=${d.originalSize}, data size=${i}`);let l=this.backend.device.createBuffer({mappedAtCreation:!0,size:a,usage:GPUBufferUsage.MAP_WRITE|GPUBufferUsage.COPY_SRC}),p=l.getMappedRange();new Uint8Array(p).set(new Uint8Array(n,o,i)),l.unmap();let m=this.backend.device.createCommandEncoder();m.copyBufferToBuffer(l,0,d.gpuData.buffer,0,a),this.backend.device.queue.submit([m.finish()]),l.destroy(),se("verbose",()=>`[WebGPU] GpuDataManager.upload(id=${t})`)}memcpy(t,r){let n=this.storageCache.get(t);if(!n)throw new Error("source gpu data for memcpy does not exist");let o=this.storageCache.get(r);if(!o)throw new Error("destination gpu data for memcpy does not exist");if(n.originalSize!==o.originalSize)throw new Error("inconsistent source and destination gpu data size");let i=eo(n.originalSize),a=this.backend.getCommandEncoder();this.backend.endComputePass(),a.copyBufferToBuffer(n.gpuData.buffer,0,o.gpuData.buffer,0,i)}registerExternalBuffer(t,r,n){let o;if(n){if(o=n[0],t===n[1])return se("verbose",()=>`[WebGPU] GpuDataManager.registerExternalBuffer(size=${r}) => id=${o}, buffer is the same, skip.`),o;if(this.backend.capturedCommandList.has(this.backend.currentSessionId))throw new Error(`Registering a different external buffer under graph capture mode is not supported yet.
             Please use the previous external buffer!`)}else o=Ya();return this.storageCache.set(o,{gpuData:{id:o,type:0,buffer:t},originalSize:r}),se("verbose",()=>`[WebGPU] GpuDataManager.registerExternalBuffer(size=${r}) => id=${o}, registered.`),o}unregisterExternalBuffer(t){t!==void 0&&(this.storageCache.delete(t),se("verbose",()=>`[WebGPU] GpuDataManager.unregisterExternalBuffer() => id=${t}`))}create(t,r=GPUBufferUsage.STORAGE|GPUBufferUsage.COPY_SRC|GPUBufferUsage.COPY_DST){let n=sm(t),o,i=(r&GPUBufferUsage.STORAGE)===GPUBufferUsage.STORAGE,a=(r&GPUBufferUsage.UNIFORM)===GPUBufferUsage.UNIFORM;if(i||a){let p=(i?this.freeBuffers:this.freeUniformBuffers).get(n);p?p.length>0?o=p.pop():o=this.backend.device.createBuffer({size:n,usage:r}):o=this.backend.device.createBuffer({size:n,usage:r})}else o=this.backend.device.createBuffer({size:n,usage:r});let d={id:Ya(),type:0,buffer:o};return this.storageCache.set(d.id,{gpuData:d,originalSize:Number(t)}),se("verbose",()=>`[WebGPU] GpuDataManager.create(size=${t}) => id=${d.id}`),d}get(t){return this.storageCache.get(t)?.gpuData}release(t){let r=typeof t=="bigint"?Number(t):t,n=this.storageCache.get(r);if(!n){if(this.storageCache.size===0)return 0;throw new Error("releasing data does not exist")}return se("verbose",()=>`[WebGPU] GpuDataManager.release(id=${r}), gpuDataId=${n.gpuData.id}`),this.storageCache.delete(r),this.buffersPending.push(n.gpuData.buffer),n.originalSize}async download(t,r){let n=this.storageCache.get(Number(t));if(!n)throw new Error("data does not exist");await ro(this.backend,n.gpuData.buffer,n.originalSize,r)}refreshPendingBuffers(){if(this.buffersPending.length!==0)if(this.backend.sessionStatus==="default"){for(let t of this.buffersPending){let r=ja.get(t.size);if((t.usage&GPUBufferUsage.STORAGE)===GPUBufferUsage.STORAGE){let n=this.freeBuffers.get(t.size)||[];r===void 0||n.length>=r?t.destroy():n.push(t)}else if((t.usage&GPUBufferUsage.UNIFORM)===GPUBufferUsage.UNIFORM){let n=this.freeUniformBuffers.get(t.size)||[];r===void 0||n.length>=r?t.destroy():n.push(t)}else t.destroy()}this.buffersPending=[]}else{let t=this.capturedPendingBuffers.get(this.backend.currentSessionId);t||(t=[],this.capturedPendingBuffers.set(this.backend.currentSessionId,t));for(let r of this.buffersPending)t.push(r);this.buffersPending=[]}}dispose(){this.freeBuffers.forEach(t=>{t.forEach(r=>{r.destroy()})}),this.freeUniformBuffers.forEach(t=>{t.forEach(r=>{r.destroy()})}),this.storageCache.forEach(t=>{t.gpuData.buffer.destroy()}),this.capturedPendingBuffers.forEach(t=>{t.forEach(r=>{r.destroy()})}),this.storageCache=new Map,this.freeBuffers=new Map,this.freeUniformBuffers=new Map,this.capturedPendingBuffers=new Map}onCreateSession(){this.sessionCount+=1}onReleaseSession(t){let r=this.capturedPendingBuffers.get(t);r&&(r.forEach(n=>{n.destroy()}),this.capturedPendingBuffers.delete(t)),this.sessionCount-=1,this.sessionCount===0&&(se("warning",()=>"[WebGPU] Clearing webgpu buffer cache"),this.storageCache.forEach(n=>{n.gpuData.buffer.destroy()}),this.storageCache=new Map)}},Qa=(...e)=>new to(...e)});var no,ee,xe=U(()=>{"use strict";no=class{constructor(t){Object.assign(this,t)}get cacheKey(){return this.key||(this.key=Object.getOwnPropertyNames(this).sort().map(t=>`${this[t]}`).join(";")),this.key}},ee=e=>new no(e)});var oo,tt,k,kt,Nr,Ja,es,ne=U(()=>{"use strict";oo=class{static calcMatMulShape(t,r){return t[1]!==r[0]?void 0:[t[0],r[1]]}},tt=class{static calcShape(t,r,n=!1){let o=t.length,i=r.length;if(o===0)return r;if(i===0)return t;let a=Math.max(t.length,r.length),d=new Array(a);if(n){if(o<2||i<2)return;let l=oo.calcMatMulShape([t[o-2],t[o-1]],[r[i-2],r[i-1]]);if(l===void 0)return;[d[a-2],d[a-1]]=l}for(let l=n?3:1;l<=a;l++){let p=o-l<0?1:t[o-l],m=i-l<0?1:r[i-l];if(p!==m&&p>1&&m>1)return;let u=Math.max(p,m);if(p&&m)d[a-l]=Math.max(p,m);else{if(u>1)return;d[a-l]=0}}return d}static isValidBroadcast(t,r){let n=t.length,o=r.length;if(n>o)return!1;for(let i=1;i<=n;i++)if(t[n-i]!==1&&t[n-i]!==r[o-i])return!1;return!0}},k=class e{static size(t){return e.getSizeFromDimensionRange(t,0,t.length)}static convertShape(t,r=4){let n=t.length;if(n===0)return[];let o=new Array(n),i=n-1;for(;i>=0;){if(t[i]%r===0){o[i]=t[i]/r;break}if(r%t[i]!==0)throw new Error("cannot convert shape");o[i]=1,r/=t[i],i--}for(i--;i>=0;i--)o[i]=t[i];return o}static sizeFromDimension(t,r){if(r<0||r>t.length)throw new Error(`invalid dimension of ${r} for sizeFromDimension as Tensor has ${t.length} dimensions.`);return e.getSizeFromDimensionRange(t,r,t.length)}static sizeToDimension(t,r){if(r<0||r>t.length)throw new Error(`invalid dimension of ${r} for sizeToDimension as Tensor has ${t.length} dimensions.`);return e.getSizeFromDimensionRange(t,0,r)}static getSizeFromDimensionRange(t,r,n){let o=1;for(let i=r;i<n;i++){if(t[i]<0)throw new Error("cannot get valid size from specified dimension range. Most likely the range contains negative values in them.");o*=Number(t[i])}return o}static computeStrides(t){let r=t.length;if(r===0)return[];if(r===1)return[1];let n=new Array(r);n[r-1]=1,n[r-2]=t[r-1];for(let o=r-3;o>=0;--o)n[o]=n[o+1]*t[o+1];return n}static normalizeAxis(t,r){if(t<-r&&t>=r)throw new Error("unsupported axis for this operation.");return t<0?t+r:t}static normalizeAxes(t,r){return t.map(n=>this.normalizeAxis(n,r??t.length))}static sortBasedOnPerm(t,r){return r?r.map(n=>t[n]):t.slice().reverse()}static padShape(t,r){let n=t.length;return t.map((o,i)=>o+r[i]+r[i+n])}static areEqual(t,r){return t.length!==r.length?!1:t.every((n,o)=>n===r[o])}},kt=class e{static adjustPoolAttributes(t,r,n,o,i,a){if(!t&&n.length!==r.length-2)throw new Error("length of specified kernel shapes should be 2 less than length of input dimensions");if(t)for(let d=0;d<r.length-2;d++)d>=n.length?n.push(r[d+2]):n[d]=r[d+2];for(let d=0;d<n.length;d++)if(d<o.length){if(o[d]<0)throw new Error("strides should be greater than or equal to 1")}else o.push(1);for(let d=0;d<n.length;d++)if(d<i.length){if(i[d]<0)throw new Error("dilations should be greater than or equal to 1")}else i.push(1);for(let d=0;d<n.length*2;d++)if(d<a.length){if(a[d]<0)throw new Error("pad should be greater than or equal to 1")}else a.push(0);for(let d=0;d<n.length;d++){if(n[d]<=0)throw new Error("kernel shapes need to be greater than 0");if(a[d]>=n[d]||a[d+n.length]>=n[d])throw new Error("pads should be smaller than kernel")}}static adjustPadsBasedOnAutoPad(t,r,n,o,i,a,d){if(d){if(i.length!==2*(t.length-2))throw new Error("length of pads should be twice the length of data dimensions");if(r.length!==t.length-2)throw new Error("length of strides should be the length of data dimensions");if(o.length!==t.length-2)throw new Error("length of kernel shapes should be the length of data dimensions");for(let l=0;l<t.length-2;l++)e.adjustPadAndReturnShape(t[l+(a?1:2)],r[l],n[l],o[l],i,l,l+t.length-2,d)}}static computePoolOutputShape(t,r,n,o,i,a,d){if(r.length<=0)throw new Error("input shape must be of size greater than 0");let l=[r[0],r[1]];return e.computeShapeHelper(t,r,l,n,o,i,a,d),l}static computeConvOutputShape(t,r,n,o,i,a,d){if(t.length<=0||r.length<=0)throw new Error("invalid input tensor dims or invalid filter tensor dims");let l=[t[0],r[0]];return e.computeShapeHelper(!1,t,l,n,o,i,a,d),l}static computeShapeHelper(t,r,n,o,i,a,d,l){if(t)for(let p=0;p<r.length-2;p++)n.push(1);else for(let p=0;p<r.length-2;p++)n.push(e.adjustPadAndReturnShape(r[p+2],o[p],i[p],a[p],d,p,p+r.length-2,l))}static adjustPadAndReturnShape(t,r,n,o,i,a,d,l){let p=n*(o-1)+1;if(l&&l!=="NOTSET")switch(l){case"VALID":return i[a]=0,i[d]=0,Math.floor((t-p)/r+1);case"SAME_LOWER":case"SAME_UPPER":if(n!==1)throw new Error("Dilation not supported for SAME_UPPER or SAME_LOWER");{let u=((t+r-1)/r-1)*r+o-t;return i[a]=Math.floor(l==="SAME_LOWER"?(u+1)/2:u/2),i[d]=u-i[a],Math.floor((t+u-o)/r+1)}default:throw new Error("Unsupported AutoPad type")}else return Math.floor((t+i[a]+i[d]-p)/r+1)}},Nr=class{static getShapeOfGemmResult(t,r,n,o,i){if(t.length!==2||n.length!==2)throw new Error("shape need to be of size 2");let a,d,l;r?(a=t[1],d=t[0]):(a=t[0],d=t[1]);let p=-1;if(o?(l=n[0],p=1):(l=n[1],p=0),n[p]!==d)throw new Error("dimension mismatch");if(a<=0||l<=0||d<=0)throw new Error("invalid shape specified");if(i&&!tt.isValidBroadcast(i,[a,l]))throw new Error("gemm: invalid bias shape for broadcast");return[a,l,d]}},Ja=-34028234663852886e22,es=34028234663852886e22});var Et,ao,ye,Ee,N,me,so,Pt,qe,q,Vr,E,M,ts,Wr,io,rs,ae=U(()=>{"use strict";J();ne();Et=64,ao=(e,t)=>{if(t===3)throw new Error("vec3 has same alignment as vec4, use vec4 instead");switch(Number(e)){case 10:return t>1?`vec${t}<f16>`:"f16";case 1:return t>1?`vec${t}<f32>`:"f32";case 6:return t>1?`vec${t}<i32>`:"i32";case 12:return t>1?`vec${t}<u32>`:"u32";case 7:if(t>1)throw new Error("currently not supported vecX of uint64 yet");return["vec2<u32>","i32"];case 13:if(t>1)throw new Error("currently not supported vecX of uint64 yet");return["vec2<u32>","u32"];case 9:if(t!==4)throw new Error("bool must be vec4");return["u32","vec4<bool>"];case 22:return"i32";case 21:return"u32";default:throw new Error(`Unknown data type: ${e}`)}},ye=(e,t=1)=>{let r=ao(e,t);return typeof r=="string"?r:r[0]},Ee=(e,t=1)=>{let r=ao(e,t);return typeof r=="string"?r:r[1]},N=(...e)=>{let t=[];return e.forEach(r=>{r.length!==0&&t.push({type:12,data:r},{type:12,data:k.computeStrides(r)})}),t},me=e=>e%4===0?4:e%2===0?2:1,so=(e="f32",t,r="0")=>!t||t===1?`${e}(${r})`:`vec${t}<${e}>(${r})`,Pt=(e,t,r)=>e==="f32"?r:t===1?`f32(${r})`:`vec${t}<f32>(${r})`,qe=(e,t)=>t===4?`(${e}.x + ${e}.y + ${e}.z + ${e}.w)`:t===2?`(${e}.x + ${e}.y)`:t===3?`(${e}.x + ${e}.y + ${e}.z)`:e,q=(e,t,r,n)=>e.startsWith("uniforms.")&&r>4?typeof t=="string"?n==="f16"?`${e}[(${t}) / 8][(${t}) % 8 / 4][(${t}) % 8 % 4]`:`${e}[(${t}) / 4][(${t}) % 4]`:n==="f16"?`${e}[${Math.floor(t/8)}][${Math.floor(t%8/4)}][${t%8%4}]`:`${e}[${Math.floor(t/4)}][${t%4}]`:r>1?`${e}[${t}]`:e,Vr=(e,t,r,n,o)=>{let i=typeof r=="number",a=i?r:r.length,d=[...new Array(a).keys()],l=a<2?"u32":a<=4?`vec${a}<u32>`:`array<u32, ${a}>`,p=ao(t,o),m=typeof p=="string"?p:p[1],u=typeof p=="string"?p:p[0],h={indices:l,value:m,storage:u,tensor:t},_=W=>typeof W=="string"?W:`${W}u`,y={offsetToIndices:!1,indicesToOffset:!1,broadcastedIndicesToOffset:!1,set:!1,setByIndices:!1,get:!1,getByIndices:!1},g=i?"uniforms.":"",x=`${g}${e}_shape`,$=`${g}${e}_strides`,v="";for(let W=0;W<a-1;W++)v+=`
    let dim${W} = current / ${q($,W,a)};
    let rest${W} = current % ${q($,W,a)};
    indices[${W}] = dim${W};
    current = rest${W};
    `;v+=`indices[${a-1}] = current;`;let S=a<2?"":`
  fn o2i_${e}(offset: u32) -> ${h.indices} {
    var indices: ${h.indices};
    var current = offset;
    ${v}
    return indices;
  }`,T=W=>(y.offsetToIndices=!0,a<2?W:`o2i_${e}(${W})`),A=[];if(a>=2)for(let W=a-1;W>=0;W--)A.push(`${q($,W,a)} * (indices[${W}])`);let C=a<2?"":`
  fn i2o_${e}(indices: ${h.indices}) -> u32 {
    return ${A.join("+")};
  }`,P=W=>(y.indicesToOffset=!0,a<2?W:`i2o_${e}(${W})`),D=(...W)=>a===0?"0u":`${h.indices}(${W.map(_).join(",")})`,R=(W,Y)=>a<2?`${W}`:`${q(W,Y,a)}`,H=(W,Y,he)=>a<2?`${W}=${he};`:`${q(W,Y,a)}=${he};`,L={},re=(W,Y)=>{y.broadcastedIndicesToOffset=!0;let he=`${Y.name}broadcastedIndicesTo${e}Offset`;if(he in L)return`${he}(${W})`;let De=[];for(let pe=a-1;pe>=0;pe--){let Ie=Y.indicesGet("outputIndices",pe+Y.rank-a);De.push(`${R($,pe)} * (${Ie} % ${R(x,pe)})`)}return L[he]=`fn ${he}(outputIndices: ${Y.type.indices}) -> u32 {
             return ${De.length>0?De.join("+"):"0u"};
           }`,`${he}(${W})`},V=(W,Y)=>(()=>{if(h.storage===h.value)return`${e}[${W}]=${Y};`;if(h.storage==="vec2<u32>"&&h.value==="i32")return`${e}[${W}]=vec2<u32>(u32(${Y}), select(0u, 0xFFFFFFFFu, ${Y} < 0));`;if(h.storage==="vec2<u32>"&&h.value==="u32")return`${e}[${W}]=vec2<u32>(u32(${Y}), 0u);`;if(h.storage==="u32"&&h.value==="vec4<bool>")return`${e}[${W}]=dot(vec4<u32>(0x1, 0x100, 0x10000, 0x1000000), vec4<u32>(${Y}));`;throw new Error(`not supported combination of storage type ${h.storage} and value type ${h.value} yet`)})(),K=W=>(()=>{if(h.storage===h.value)return`${e}[${W}]`;if(h.storage==="vec2<u32>"&&h.value==="i32")return`i32(${e}[${W}].x)`;if(h.storage==="vec2<u32>"&&h.value==="u32")return`u32(${e}[${W}].x)`;if(h.storage==="u32"&&h.value==="vec4<bool>")return`vec4<bool>(bool(${e}[${W}] & 0xFFu), bool(${e}[${W}] & 0xFF00u), bool(${e}[${W}] & 0xFF0000u), bool(${e}[${W}] & 0xFF000000u))`;throw new Error(`not supported combination of storage type ${h.storage} and value type ${h.value} yet`)})(),we=a<2?"":`
  fn get_${e}ByIndices(indices: ${h.indices}) -> ${m} {
    return ${K(`i2o_${e}(indices)`)};
  }`,j=a<2?"":(()=>{let W=d.map(he=>`d${he}: u32`).join(", "),Y=d.map(he=>`d${he}`).join(", ");return`
  fn get_${e}(${W}) -> ${m} {
    return get_${e}ByIndices(${D(Y)});
  }`})(),Q=(...W)=>{if(W.length!==a)throw new Error(`indices length must be ${a}`);let Y=W.map(_).join(",");return a===0?K("0u"):a===1?K(Y[0]):(y.get=!0,y.getByIndices=!0,y.indicesToOffset=!0,`get_${e}(${Y})`)},ie=W=>a<2?K(W):(y.getByIndices=!0,y.indicesToOffset=!0,`get_${e}ByIndices(${W})`),te=a<2?"":`
  fn set_${e}ByIndices(indices: ${h.indices}, value: ${m}) {
    ${V(`i2o_${e}(indices)`,"value")}
  }`,be=a<2?"":(()=>{let W=d.map(he=>`d${he}: u32`).join(", "),Y=d.map(he=>`d${he}`).join(", ");return`
  fn set_${e}(${W}, value: ${m}) {
    set_${e}ByIndices(${D(Y)}, value);
  }`})();return{impl:()=>{let W=[],Y=!1;return y.offsetToIndices&&(W.push(S),Y=!0),y.indicesToOffset&&(W.push(C),Y=!0),y.broadcastedIndicesToOffset&&(Object.values(L).forEach(he=>W.push(he)),Y=!0),y.set&&(W.push(be),Y=!0),y.setByIndices&&(W.push(te),Y=!0),y.get&&(W.push(j),Y=!0),y.getByIndices&&(W.push(we),Y=!0),!i&&Y&&W.unshift(`const ${x} = ${h.indices}(${r.join(",")});`,`const ${$} = ${h.indices}(${k.computeStrides(r).join(",")});`),W.join(`
`)},type:h,offsetToIndices:T,indicesToOffset:P,broadcastedIndicesToOffset:re,indices:D,indicesGet:R,indicesSet:H,set:(...W)=>{if(W.length!==a+1)throw new Error(`indices length must be ${a}`);let Y=W[a];if(typeof Y!="string")throw new Error("value must be string");let he=W.slice(0,a).map(_).join(",");return a===0?V("0u",Y):a===1?V(he[0],Y):(y.set=!0,y.setByIndices=!0,y.indicesToOffset=!0,`set_${e}(${he}, ${Y})`)},setByOffset:V,setByIndices:(W,Y)=>a<2?V(W,Y):(y.setByIndices=!0,y.indicesToOffset=!0,`set_${e}ByIndices(${W}, ${Y});`),get:Q,getByOffset:K,getByIndices:ie,usage:n,name:e,strides:$,shape:x,rank:a}},E=(e,t,r,n=1)=>Vr(e,t,r,"input",n),M=(e,t,r,n=1)=>Vr(e,t,r,"output",n),ts=(e,t,r)=>Vr(e,t,r,"atomicOutput",1),Wr=(e,t,r,n=1)=>Vr(e,t,r,"internal",n),io=class{constructor(t,r){this.normalizedDispatchGroup=t;this.limits=r;this.internalVariables=[];this.variables=[];this.uniforms=[];this.variableIndex=0}guardAgainstOutOfBoundsWorkgroupSizes(t){return`if (global_idx >= ${typeof t=="number"?`${t}u`:t}) { return; }`}mainStart(t=Et){let r=typeof t=="number"?t:t[0],n=typeof t=="number"?1:t[1],o=typeof t=="number"?1:t[2];if(r>this.limits.maxComputeWorkgroupSizeX||n>this.limits.maxComputeWorkgroupSizeY||o>this.limits.maxComputeWorkgroupSizeZ)throw new Error(`workgroup size [${r}, ${n}, ${o}] exceeds the maximum workgroup size [${this.limits.maxComputeWorkgroupSizeX}, ${this.limits.maxComputeWorkgroupSizeY}, ${this.limits.maxComputeWorkgroupSizeZ}].`);if(r*n*o>this.limits.maxComputeInvocationsPerWorkgroup)throw new Error(`workgroup size [${r}, ${n}, ${o}] exceeds the maximum workgroup invocations ${this.limits.maxComputeInvocationsPerWorkgroup}.`);let i=this.normalizedDispatchGroup[1]===1&&this.normalizedDispatchGroup[2]===1,a=i?`@builtin(global_invocation_id) global_id : vec3<u32>,
    @builtin(workgroup_id) workgroup_id : vec3<u32>,
    @builtin(local_invocation_index) local_idx : u32,
    @builtin(local_invocation_id) local_id : vec3<u32>`:`@builtin(global_invocation_id) global_id : vec3<u32>,
                                             @builtin(local_invocation_id) local_id : vec3<u32>,
    @builtin(local_invocation_index) local_idx : u32,
    @builtin(workgroup_id) workgroup_id : vec3<u32>,
    @builtin(num_workgroups) num_workgroups : vec3<u32>`,d=i?`let global_idx = global_id.x;
         let workgroup_index = workgroup_id.x;`:`let workgroup_index = workgroup_id.z * num_workgroups[0] * num_workgroups[1] +
             workgroup_id.y * num_workgroups[0] + workgroup_id.x;
         let global_idx = workgroup_index * ${r*n*o}u + local_idx;`;return`@compute @workgroup_size(${r}, ${n}, ${o})
  fn main(${a}) {
    ${d}
  `}appendVariableUniforms(t){t.rank!==0&&(t.shape.startsWith("uniforms.")&&this.uniforms.push({name:t.shape.replace("uniforms.",""),type:"u32",length:t.rank}),t.strides.startsWith("uniforms.")&&this.uniforms.push({name:t.strides.replace("uniforms.",""),type:"u32",length:t.rank}))}declareVariable(t,r){if(t.usage==="internal")throw new Error("cannot use internal variable with declareVariable(). use registerInternalVariables() instead.");this.variables.push(t),this.appendVariableUniforms(t);let n=t.usage==="input"?"read":"read_write",o=t.usage==="atomicOutput"?"atomic<i32>":t.type.storage;return`@group(0) @binding(${r}) var<storage, ${n}> ${t.name}: array<${o}>;`}declareVariables(...t){return t.map(r=>this.declareVariable(r,this.variableIndex++)).join(`
`)}registerInternalVariable(t){if(t.usage!=="internal")throw new Error("cannot use input or output variable with registerInternalVariable(). use declareVariables() instead.");this.internalVariables.push(t),this.appendVariableUniforms(t)}registerInternalVariables(...t){return t.forEach(r=>this.registerInternalVariable(r)),this}registerUniform(t,r,n=1){return this.uniforms.push({name:t,type:r,length:n}),this}registerUniforms(t){return this.uniforms=this.uniforms.concat(t),this}uniformDeclaration(){if(this.uniforms.length===0)return"";let t=[];for(let{name:r,type:n,length:o}of this.uniforms)if(o&&o>4)n==="f16"?t.push(`@align(16) ${r}:array<mat2x4<${n}>, ${Math.ceil(o/8)}>`):t.push(`${r}:array<vec4<${n}>, ${Math.ceil(o/4)}>`);else{let i=o==null||o===1?n:`vec${o}<${n}>`;t.push(`${r}:${i}`)}return`
      struct Uniforms { ${t.join(", ")} };
      @group(0) @binding(${this.variableIndex}) var<uniform> uniforms: Uniforms;`}get additionalImplementations(){return this.uniformDeclaration()+this.variables.map(t=>t.impl()).join(`
`)+this.internalVariables.map(t=>t.impl()).join(`
`)}get variablesInfo(){if(this.uniforms.length===0)return;let t=r=>[12,10,1,6][["u32","f16","f32","i32"].indexOf(r)];return this.uniforms.map(r=>[t(r.type),r.length??1])}},rs=(e,t)=>new io(e,t)});var dm,ns,lm,cm,pm,mm,Pe,os,is,dt=U(()=>{"use strict";J();ne();xe();ae();dm=(e,t)=>{if(!e||e.length!==1)throw new Error("Transpose requires 1 input.");if(t.length!==0&&t.length!==e[0].dims.length)throw new Error(`perm size ${t.length} does not match input rank ${e[0].dims.length}`)},ns=(e,t)=>t.length!==0?t:[...new Array(e).keys()].reverse(),lm=(e,t)=>k.sortBasedOnPerm(e,ns(e.length,t)),cm=(e,t,r,n)=>{let o=`fn perm(i: ${n.type.indices}) -> ${r.type.indices} {
    var a: ${r.type.indices};`;for(let i=0;i<t;++i)o+=`a[${e[i]}]=i[${i}];`;return o+="return a;}"},pm=(e,t)=>{let r=[],n=[];for(let o=0;o<e.length;++o)e[o]!==1&&r.push(e[o]),e[t[o]]!==1&&n.push(t[o]);return{newShape:r,newPerm:n}},mm=(e,t)=>{let r=0;for(let n=0;n<e.length;++n)if(t[e[n]]!==1){if(e[n]<r)return!1;r=e[n]}return!0},Pe=(e,t)=>{let r=e.dataType,n=e.dims.length,o=ns(n,t),i=lm(e.dims,o),a=e.dims,d=i,l=n<2||mm(o,e.dims),p;if(l)return p=g=>{let x=E("input",r,a,4),$=M("output",r,d,4);return`
  ${g.registerUniform("output_size","u32").declareVariables(x,$)}
  ${g.mainStart()}
    ${g.guardAgainstOutOfBoundsWorkgroupSizes("uniforms.output_size")}
    output[global_idx] = input[global_idx];
  }`},{name:"TransposeCopy",shaderCache:{inputDependencies:["type"]},getRunData:()=>{let g=k.size(i);return{outputs:[{dims:i,dataType:e.dataType}],dispatchGroup:{x:Math.ceil(g/64/4)},programUniforms:[{type:12,data:Math.ceil(g/4)}]}},getShaderSource:p};let{newShape:m,newPerm:u}=pm(e.dims,o),h=k.areEqual(u,[2,3,1]),_=k.areEqual(u,[3,1,2]);if(m.length===2||h||_){a=h?[m[0],m[1]*m[2]]:_?[m[0]*m[1],m[2]]:m,d=[a[1],a[0]];let g=16;return p=x=>{let $=E("a",r,a.length),v=M("output",r,d.length);return`
  ${x.registerUniform("output_size","u32").declareVariables($,v)}
  var<workgroup> tile : array<array<${v.type.value}, ${g+1}>, ${g}>;
  ${x.mainStart([g,g,1])}
    let stride = (uniforms.output_shape[1] - 1) / ${g} + 1;
    let workgroup_id_x = workgroup_index % stride;
    let workgroup_id_y = workgroup_index / stride;
    let input_col = workgroup_id_y * ${g}u + local_id.x;
    let input_row = workgroup_id_x * ${g}u + local_id.y;
    if (input_row < uniforms.a_shape[0] && input_col < uniforms.a_shape[1]) {
      tile[local_id.y][local_id.x] = ${$.getByIndices(`${$.type.indices}(input_row, input_col)`)};
    }
    workgroupBarrier();

    let output_col = workgroup_id_x * ${g}u + local_id.x;
    let output_row = workgroup_id_y * ${g}u + local_id.y;
    if (output_row < uniforms.output_shape[0] && output_col < uniforms.output_shape[1]) {
      ${v.setByIndices(`${v.type.indices}(output_row, output_col)`,"tile[local_id.x][local_id.y]")}
    }
  }`},{name:"TransposeShared",shaderCache:{inputDependencies:["type"]},getRunData:()=>{let x=k.size(i);return{outputs:[{dims:i,dataType:e.dataType}],dispatchGroup:{x:Math.ceil(d[1]/g),y:Math.ceil(d[0]/g)},programUniforms:[{type:12,data:x},...N(a,d)]}},getShaderSource:p}}return p=g=>{let x=E("a",r,a.length),$=M("output",r,d.length);return`
  ${g.registerUniform("output_size","u32").declareVariables(x,$)}

  ${cm(o,n,x,$)}

  ${g.mainStart()}
    ${g.guardAgainstOutOfBoundsWorkgroupSizes("uniforms.output_size")}

    let indices = ${$.offsetToIndices("global_idx")};
    let aIndices = perm(indices);

    ${$.setByOffset("global_idx",x.getByIndices("aIndices"))}
  }`},{name:"Transpose",shaderCache:{hint:`${t}`,inputDependencies:["rank"]},getRunData:()=>{let g=k.size(i);return{outputs:[{dims:i,dataType:e.dataType}],dispatchGroup:{x:Math.ceil(g/64)},programUniforms:[{type:12,data:g},...N(a,d)]}},getShaderSource:p}},os=(e,t)=>{dm(e.inputs,t.perm),e.compute(Pe(e.inputs[0],t.perm))},is=e=>ee({perm:e.perm})});var fm,hm,gm,bm,ym,_m,wm,vm,$m,xm,rt,as,ss,us,ds,ls,cs,ps,ms,fs,hs,gs=U(()=>{"use strict";J();ne();ae();Lr();dt();fm={max:"select(bestValue, candidate, candidate > bestValue)",min:"select(bestValue, candidate, candidate < bestValue)",mean:"bestValue + candidate",sum:"bestValue + candidate",prod:"bestValue * candidate",sumSquare:"bestValue + candidate * candidate",logSumExp:"bestValue + exp(candidate)",l1:"bestValue + abs(candidate)",l2:"bestValue + candidate * candidate",logSum:"bestValue + candidate"},hm={max:"select(bestValue, candidate, candidate > bestValue)",min:"select(bestValue, candidate, candidate < bestValue)",mean:"bestValue + candidate",sum:"bestValue + candidate",prod:"bestValue * candidate",sumSquare:"bestValue + candidate",logSumExp:"bestValue + candidate",l1:"bestValue + candidate",l2:"bestValue + candidate",logSum:"bestValue + candidate"},gm={max:"_A[offset]",min:"_A[offset]",mean:"0",sum:"0",prod:"1",sumSquare:"0",logSumExp:"0",l1:"0",l2:"0",logSum:"0"},bm={max:"bestValue",min:"bestValue",sum:"bestValue",prod:"bestValue",sumSquare:"bestValue",logSumExp:"log(bestValue)",l1:"bestValue",l2:"sqrt(bestValue)",logSum:"log(bestValue)"},ym=(e,t)=>{let r=[];for(let n=t-e;n<t;++n)r.push(n);return r},_m=(e,t)=>{let r=[],n=e.length;for(let i=0;i<n;i++)t.indexOf(i)===-1&&r.push(e[i]);let o=t.map(i=>e[i]);return[r,o]},wm=(e,t)=>{let r=e.length+t.length,n=[],o=0;for(let i=0;i<r;i++)t.indexOf(i)===-1?n.push(e[o++]):n.push(1);return n},vm=(e,t)=>{for(let r=0;r<e.length;++r)if(e[e.length-r-1]!==t-1-r)return!1;return!0},$m=(e,t)=>{let r=[];if(!vm(e,t)){for(let n=0;n<t;++n)e.indexOf(n)===-1&&r.push(n);e.forEach(n=>r.push(n))}return r},xm=(e,t,r,n,o,i,a)=>{let d=r[0].dims,l=k.size(i),p=k.size(a),m=E("_A",r[0].dataType,d),u=M("output",o,i),h=64;l===1&&(h=256);let _=`
          var<workgroup> aBestValues : array<f32, ${h}>;
       `,y=g=>`
        ${g.registerUniform("reduceSize","u32").declareVariables(m,u)}
        ${_}
        fn DIV_CEIL(a : u32, b : u32) -> u32 {
          return ((a - 1u) / b + 1u);
         }
         ${g.mainStart(h)}

          let outputIndex = global_idx / ${h};
          let offset = outputIndex * uniforms.reduceSize;

          var bestValue = f32(${gm[n]});
          let Length = uniforms.reduceSize;
          for (var k = local_idx; k < Length; k = k + ${h}) {
           let candidate = f32(${m.getByOffset("offset + k")});
           bestValue = ${fm[n]};
          }
          aBestValues[local_idx] = bestValue;
          workgroupBarrier();

         var reduceSize = min(Length, ${h}u);
         for (var currentSize = reduceSize / 2u; reduceSize > 1u;
             currentSize = reduceSize / 2u) {
           let interval = DIV_CEIL(reduceSize, 2u);
           if (local_idx < currentSize) {
            let candidate = aBestValues[local_idx + interval];
            bestValue = ${hm[n]};
            aBestValues[local_idx] = bestValue;
           }
           reduceSize = interval;
           workgroupBarrier();
         }

         if (local_idx == 0u) {
          ${u.setByOffset("outputIndex",`${n==="mean"?`${u.type.storage}(bestValue / f32(uniforms.reduceSize))`:`${u.type.storage}(${bm[n]})`}`)};
         }
        }`;return{name:e,shaderCache:{hint:`${t};${h}`,inputDependencies:["type"]},getShaderSource:y,getRunData:()=>({outputs:[{dims:i,dataType:o}],dispatchGroup:{x:l},programUniforms:[{type:12,data:p}]})}},rt=(e,t,r,n)=>{let o=e.inputs.length===1?r:uo(e.inputs,r),i=o.axes;i.length===0&&!o.noopWithEmptyAxes&&(i=e.inputs[0].dims.map((_,y)=>y));let a=k.normalizeAxes(i,e.inputs[0].dims.length),d=a,l=e.inputs[0],p=$m(d,e.inputs[0].dims.length);p.length>0&&(l=e.compute(Pe(e.inputs[0],p),{inputs:[0],outputs:[-1]})[0],d=ym(d.length,l.dims.length));let[m,u]=_m(l.dims,d),h=m;o.keepDims&&(h=wm(m,a)),e.compute(xm(t,o.cacheKey,[l],n,e.inputs[0].dataType,h,u),{inputs:[l]})},as=(e,t)=>{rt(e,"ReduceMeanShared",t,"mean")},ss=(e,t)=>{rt(e,"ReduceL1Shared",t,"l1")},us=(e,t)=>{rt(e,"ReduceL2Shared",t,"l2")},ds=(e,t)=>{rt(e,"ReduceLogSumExpShared",t,"logSumExp")},ls=(e,t)=>{rt(e,"ReduceMaxShared",t,"max")},cs=(e,t)=>{rt(e,"ReduceMinShared",t,"min")},ps=(e,t)=>{rt(e,"ReduceProdShared",t,"prod")},ms=(e,t)=>{rt(e,"ReduceSumShared",t,"sum")},fs=(e,t)=>{rt(e,"ReduceSumSquareShared",t,"sumSquare")},hs=(e,t)=>{rt(e,"ReduceLogSumShared",t,"logSum")}});var nt,Sm,Gr,uo,ot,Tm,Im,Cm,Am,km,Em,Pm,zm,Om,Dm,it,bs,ys,_s,ws,vs,$s,xs,Ss,Ts,Is,Lr=U(()=>{"use strict";J();ne();xe();ae();gs();nt=e=>{if(!e||e.length===0||e.length>2)throw new Error("Reduce op requires 1 or 2 inputs.");if(e.length===2&&e[1].dims.length!==1)throw new Error("Invalid axes input dims.")},Sm=e=>["","",`var value = ${e.getByIndices("input_indices")};`,""],Gr=(e,t,r,n,o,i,a=!1,d=!1)=>{let l=[],p=r[0].dims,m=p.length,u=k.normalizeAxes(o,m),h=!d&&u.length===0;p.forEach((x,$)=>{h||u.indexOf($)>=0?a&&l.push(1):l.push(x)});let _=l.length,y=k.size(l);return{name:e,shaderCache:t,getShaderSource:x=>{let $=[],v=E("_A",r[0].dataType,m),S=M("output",i,_),T=n(v,S,u),A=T[2];for(let C=0,P=0;C<m;C++)h||u.indexOf(C)>=0?(a&&P++,A=`for(var j${C}: u32 = 0; j${C} < ${p[C]}; j${C}++) {
                  ${T[2].includes("last_index")?`let last_index = j${C};`:""}
                  ${v.indicesSet("input_indices",C,`j${C}`)}
                  ${A}
                }`):($.push(`${v.indicesSet("input_indices",C,S.indicesGet("output_indices",P))};`),P++);return`

        ${x.registerUniform("output_size","u32").declareVariables(v,S)}

        ${x.mainStart()}
          ${x.guardAgainstOutOfBoundsWorkgroupSizes("uniforms.output_size")}
          var input_indices: ${v.type.indices};
          let output_indices = ${S.offsetToIndices("global_idx")};

          ${$.join(`
`)}
          ${T[0]}       // init ops for reduce max/min
          ${T[1]}
          ${A}
          ${T[3]}
          ${T.length===4?S.setByOffset("global_idx","value"):T.slice(4).join(`
`)}
        }`},getRunData:()=>({outputs:[{dims:l,dataType:i}],dispatchGroup:{x:Math.ceil(y/64)},programUniforms:[{type:12,data:y},...N(p,l)]})}},uo=(e,t)=>{let r=[];return e[1].dims[0]>0&&e[1].getBigInt64Array().forEach(n=>r.push(Number(n))),ee({axes:r,keepDims:t.keepDims,noopWithEmptyAxes:t.noopWithEmptyAxes})},ot=(e,t,r,n)=>{let o=e.inputs,i=o.length===1?r:uo(o,r);e.compute(Gr(t,{hint:i.cacheKey,inputDependencies:["rank"]},[o[0]],i.noopWithEmptyAxes&&i.axes.length===0?Sm:n,i.axes,o[0].dataType,i.keepDims,i.noopWithEmptyAxes),{inputs:[0]})},Tm=(e,t)=>{nt(e.inputs),ot(e,"ReduceLogSum",t,(n,o)=>[`var value = ${o.type.storage}(0);`,"",`value += ${n.getByIndices("input_indices")};`,"value = log(value);"])},Im=(e,t)=>{nt(e.inputs),ot(e,"ReduceL1",t,(n,o)=>[`var value = ${o.type.storage}(0);`,"",`value += abs(${n.getByIndices("input_indices")});`,""])},Cm=(e,t)=>{nt(e.inputs),ot(e,"ReduceL2",t,(n,o)=>[`var t = ${o.type.value}(0); var value = ${o.type.value}(0);`,"",`t = ${n.getByIndices("input_indices")}; value += (t * t);`,"value = sqrt(value);"])},Am=(e,t)=>{nt(e.inputs),ot(e,"ReduceLogSumExp",t,(n,o)=>[`var value = ${o.type.storage}(0);`,"",`value += exp(${n.getByIndices("input_indices")});`,"value = log(value);"])},km=(e,t)=>{nt(e.inputs),ot(e,"ReduceMax",t,(n,o,i)=>{let a=[];for(let d=0;d<n.rank;d++)(i.indexOf(d)>=0||i.length===0)&&a.push(n.indicesSet("input_indices",d,0));return[`${a.join(`
`)}`,`var value = ${n.getByIndices("input_indices")};`,`value = max(value, ${n.getByIndices("input_indices")});`,""]})},Em=(e,t)=>{nt(e.inputs),ot(e,"ReduceMean",t,(n,o,i)=>{let a=1;for(let d=0;d<n.rank;d++)(i.indexOf(d)>=0||i.length===0)&&(a*=e.inputs[0].dims[d]);return["var sum = f32(0);","",`sum += f32(${n.getByIndices("input_indices")});`,`let value = ${o.type.value}(sum / ${a});`]})},Pm=(e,t)=>{nt(e.inputs),ot(e,"ReduceMin",t,(n,o,i)=>{let a=[];for(let d=0;d<n.rank;d++)(i.indexOf(d)>=0||i.length===0)&&a.push(`input_indices[${d}] = 0;`);return[`${a.join(`
`)}`,`var value = ${n.getByIndices("input_indices")};`,`value = min(value, ${n.getByIndices("input_indices")});`,""]})},zm=(e,t)=>{nt(e.inputs),ot(e,"ReduceProd",t,(n,o)=>[`var value = ${o.type.storage}(1);`,"",`value *= ${n.getByIndices("input_indices")};`,""])},Om=(e,t)=>{nt(e.inputs),ot(e,"ReduceSum",t,(n,o)=>[`var value = ${o.type.storage}(0);`,"",`value += ${n.getByIndices("input_indices")};`,""])},Dm=(e,t)=>{nt(e.inputs),ot(e,"ReduceSumSquare",t,(n,o)=>[`var t = ${o.type.value}(0); var value = ${o.type.value}(0);`,"",`t = ${n.getByIndices("input_indices")}; value += t * t;`,""])},it=(e,t,r)=>{if(t.length===0)return r;let n=1,o=1;for(let i=0;i<t.length;i++)t.indexOf(i)===-1?n*=e[i]:o*=e[i];return o<32&&n>1024},bs=(e,t)=>{it(e.inputs[0].dims,t.axes,t.noopWithEmptyAxes)?Em(e,t):as(e,t)},ys=(e,t)=>{it(e.inputs[0].dims,t.axes,t.noopWithEmptyAxes)?Im(e,t):ss(e,t)},_s=(e,t)=>{it(e.inputs[0].dims,t.axes,t.noopWithEmptyAxes)?Cm(e,t):us(e,t)},ws=(e,t)=>{it(e.inputs[0].dims,t.axes,t.noopWithEmptyAxes)?Am(e,t):ds(e,t)},vs=(e,t)=>{it(e.inputs[0].dims,t.axes,t.noopWithEmptyAxes)?km(e,t):ls(e,t)},$s=(e,t)=>{it(e.inputs[0].dims,t.axes,t.noopWithEmptyAxes)?Pm(e,t):cs(e,t)},xs=(e,t)=>{it(e.inputs[0].dims,t.axes,t.noopWithEmptyAxes)?zm(e,t):ps(e,t)},Ss=(e,t)=>{it(e.inputs[0].dims,t.axes,t.noopWithEmptyAxes)?Om(e,t):ms(e,t)},Ts=(e,t)=>{it(e.inputs[0].dims,t.axes,t.noopWithEmptyAxes)?Dm(e,t):fs(e,t)},Is=(e,t)=>{it(e.inputs[0].dims,t.axes,t.noopWithEmptyAxes)?Tm(e,t):hs(e,t)}});var Cs,As,ks,lo,Es=U(()=>{"use strict";J();xe();Lr();Cs=e=>{if(!e||e.length===0||e.length>2)throw new Error("ArgMinMaxOp op requires 1 or 2 inputs.");if(e[0].dataType!==1)throw new Error("Invalid input type.")},As=(e,t)=>{Cs(e.inputs);let r=(n,o,i)=>{let a=[];for(let d=0;d<n.rank;d++)(i.indexOf(d)>=0||i.length===0)&&a.push(`input_indices[${d}] = 0;`);return[`${a.join(`
`)}`,`var value = ${n.getByIndices("input_indices")};
var best_index : i32 = 0;`,`if (${n.getByIndices("input_indices")} ${t.selectLastIndex>0?"<=":"<"} value) {
         value = ${n.getByIndices("input_indices")};
         best_index = i32(last_index);
       }`,"",o.setByOffset("global_idx","best_index")]};e.compute(Gr("ArgMin",{hint:t.cacheKey,inputDependencies:["rank"]},[e.inputs[0]],r,[t.axis],7,t.keepDims),{inputs:[0]})},ks=(e,t)=>{Cs(e.inputs);let r=(n,o,i)=>{let a=[];for(let d=0;d<n.rank;d++)(i.indexOf(d)>=0||i.length===0)&&a.push(`input_indices[${d}] = 0;`);return[`${a.join(`
`)}`,`var value = ${n.getByIndices("input_indices")};
var best_index : i32 = 0;`,`if (${n.getByIndices("input_indices")} ${t.selectLastIndex>0?">=":">"} value) {
         value = ${n.getByIndices("input_indices")};
         best_index = i32(last_index);
       }`,"",o.setByOffset("global_idx","best_index")]};e.compute(Gr("argMax",{hint:t.cacheKey,inputDependencies:["rank"]},[e.inputs[0]],r,[t.axis],7,t.keepDims),{inputs:[0]})},lo=e=>ee(e)});var Bm,co,Mm,Rm,Um,Ut,Nm,Ps,Hr=U(()=>{"use strict";J();ne();Ur();ae();Bm=(e,t)=>{let r=e[0],n=e[1],o=e[2],i=e[3],a=e[4],d=e[5];if(a&&d)throw new Error("Attention cannot have both past and attention_bias");if(r.dims.length!==3)throw new Error('Input "input" must have 3 dimensions');let l=r.dims[0],p=r.dims[1],m=r.dims[2];if(o.dims.length!==1)throw new Error('Input "bias" is expected to have 1 dimensions');if(n.dims.length!==2)throw new Error('Input "weights" is expected to have 2 dimensions');if(n.dims[0]!==m)throw new Error("Input 1 dimension 0 should have same length as dimension 2 of input 0");if(o.dims[0]!==n.dims[1])throw new Error('Input "bias" dimension 0 should have same length as dimension 1 of input "weights"');let u=o.dims[0]/3,h=u,_=h;if(t.qkvHiddenSizes.length>0){if(t.qkvHiddenSizes.length!==3)throw new Error("qkv_hidden_sizes attribute should have 3 elements");for(let S of t.qkvHiddenSizes)if(S%t.numHeads!==0)throw new Error("qkv_hidden_sizes should be divisible by num_heads");u=t.qkvHiddenSizes[0],h=t.qkvHiddenSizes[1],_=t.qkvHiddenSizes[2]}let y=p;if(u!==h)throw new Error("qkv_hidden_sizes first element should be same as the second");if(o.dims[0]!==u+h+_)throw new Error('Input "bias" dimension 0 should have same length as sum of Q/K/V hidden sizes');let g=0;if(a){if(h!==_)throw new Error('Input "past" expect k_hidden_size == v_hidden_size');if(a.dims.length!==5)throw new Error('Input "past" must have 5 dimensions');if(a.dims[0]!==2)throw new Error('Input "past" first dimension must be 2');if(a.dims[1]!==l)throw new Error('Input "past" second dimension must be batch_size');if(a.dims[2]!==t.numHeads)throw new Error('Input "past" third dimension must be num_heads');if(a.dims[4]!==h/t.numHeads)throw new Error('Input "past" fifth dimension must be k_hidden_size / num_heads');t.pastPresentShareBuffer||(g=a.dims[3])}let x=y+g,$=-1,v=0;if(i)throw new Error("Mask not supported");if(a)throw new Error("past is not supported");if(d){if(d.dims.length!==4)throw new Error('Input "attention_bias" must have 4 dimensions');if(d.dims[0]!==l||d.dims[1]!==t.numHeads||d.dims[2]!==p||d.dims[3]!==x)throw new Error('Expect "attention_bias" shape (batch_size, num_heads, sequence_length, total_sequence_length)')}return{batchSize:l,sequenceLength:p,pastSequenceLength:g,kvSequenceLength:y,totalSequenceLength:x,maxSequenceLength:$,inputHiddenSize:m,hiddenSize:u,vHiddenSize:_,headSize:Math.floor(u/t.numHeads),vHeadSize:Math.floor(_/t.numHeads),numHeads:t.numHeads,isUnidirectional:!1,pastPresentShareBuffer:!1,maskFilterValue:t.maskFilterValue,maskType:v,scale:t.scale,broadcastResPosBias:!1,passPastInKv:!1,qkvFormat:1}},co=(e,t,r)=>t&&e?`
      let total_sequence_length_input = u32(${t.getByOffset("0")});
      let present_sequence_length = max(total_sequence_length_input, uniforms.past_sequence_length);
      let is_subsequent_prompt: bool = sequence_length > 1 && sequence_length != total_sequence_length_input;
      let is_first_prompt: bool = is_subsequent_prompt == false && sequence_length == total_sequence_length_input;
      total_sequence_length = u32(${e?.getByOffset("batchIdx")}) + 1;
      var past_sequence_length: u32 = 0;
      if (is_first_prompt == false) {
        past_sequence_length = total_sequence_length - sequence_length;
      }
       `:`
    ${r?"let past_sequence_length = uniforms.past_sequence_length":""};
    let present_sequence_length = total_sequence_length;
    `,Mm=(e,t,r,n,o,i,a,d)=>{let l=me(a?1:i),p=64,m=i/l;m<p&&(p=32);let u=Math.ceil(i/l/p),h=[{type:12,data:t},{type:12,data:r},{type:12,data:n},{type:12,data:o},{type:12,data:m},{type:12,data:u}],_=ye(e.dataType,l),y=Ee(1,l),g=["type"];a&&g.push("type"),d&&g.push("type");let x=$=>{let v=M("x",e.dataType,e.dims,l),S=[v],T=a?E("seq_lens",a.dataType,a.dims):void 0;T&&S.push(T);let A=d?E("total_sequence_length_input",d.dataType,d.dims):void 0;A&&S.push(A);let C=Ee(e.dataType),P=[{name:"batch_size",type:"u32"},{name:"num_heads",type:"u32"},{name:"past_sequence_length",type:"u32"},{name:"sequence_length",type:"u32"},{name:"total_sequence_length",type:"u32"},{name:"elements_per_thread",type:"u32"}];return`
  var<workgroup> thread_max: array<f32, ${p}>;
  var<workgroup> thread_sum: array<f32, ${p}>;
  ${$.registerUniforms(P).declareVariables(...S)}
  ${$.mainStart([p,1,1])}
    let batchIdx = workgroup_id.z / uniforms.num_heads;
    let headIdx = workgroup_id.z % uniforms.num_heads;
    let sequence_length = uniforms.sequence_length;
    var total_sequence_length = uniforms.total_sequence_length;
    ${co(T,A,!1)}
    let local_offset = local_idx * uniforms.elements_per_thread;
    let offset = (global_idx / ${p}) * uniforms.total_sequence_length + local_offset;
    let seq_causal_length = ${a?"u32(past_sequence_length + workgroup_id.y + 1)":"total_sequence_length"};
    var thread_max_vector = ${y}(-3.402823e+38f);
    for (var i: u32 = 0; i < uniforms.elements_per_thread && i + local_offset < seq_causal_length; i++) {
      thread_max_vector = max(${y}(x[offset + i]), thread_max_vector);
    }
    thread_max[local_idx] = ${(()=>{switch(l){case 1:return"thread_max_vector";case 2:return"max(thread_max_vector.x, thread_max_vector.y)";case 4:return"max(max(thread_max_vector.x, thread_max_vector.y), max(thread_max_vector.z, thread_max_vector.w))";default:throw new Error(`Unsupported components: ${l}`)}})()};
    workgroupBarrier();

    var max_value =  f32(-3.402823e+38f);
    for (var i = 0u; i < ${p}; i++) {
      max_value = max(thread_max[i], max_value);
    }

    var sum_vector = ${y}(0);
    for (var i: u32 = 0; i < uniforms.elements_per_thread && i + local_offset < seq_causal_length; i++) {
      sum_vector += exp(${y}(x[offset + i]) - max_value);
    }
    thread_sum[local_idx] = ${(()=>{switch(l){case 1:return"sum_vector";case 2:return"sum_vector.x + sum_vector.y";case 4:return"sum_vector.x + sum_vector.y + sum_vector.z + sum_vector.w";default:throw new Error(`Unsupported components: ${l}`)}})()};
    workgroupBarrier();

    var sum: f32 = 0;
    for (var i = 0u; i < ${p}; i++) {
      sum += thread_sum[i];
    }

    if (sum == 0) {
      for (var i: u32 = 0; i < uniforms.elements_per_thread && i + local_offset < seq_causal_length; i++) {
        x[offset + i] = ${v.type.value}(${C}(1.0) / ${C}(seq_causal_length));
      }
    } else {
      for (var i: u32 = 0; i < uniforms.elements_per_thread && i + local_offset < seq_causal_length; i++) {
        var f32input = ${y}(x[offset + i]);
        x[offset + i] = ${v.type.value}(exp(f32input - max_value) / sum);
      }
    }
      ${a?`
        for (var total_seq_id: u32 = seq_causal_length; total_seq_id + local_offset < uniforms.total_sequence_length; total_seq_id++) {
          x[offset + total_seq_id] = ${v.type.value}(${C}(0));
        }`:""};
  }`};return{name:"AttentionProbsSoftmax",shaderCache:{hint:`${p};${_};${l}`,inputDependencies:g},getShaderSource:x,getRunData:()=>({outputs:[],dispatchGroup:{x:Math.ceil(i/p),y:o,z:t*r},programUniforms:h})}},Rm=(e,t,r,n,o,i,a,d,l)=>{let p=a+i.kvSequenceLength,m=[i.batchSize,i.numHeads,i.sequenceLength,p],u=e>1&&n,h=i.kvNumHeads?i.kvNumHeads:i.numHeads,_=u?[i.batchSize,h,p,i.headSize]:void 0,y=i.nReps?i.nReps:1,g=i.scale===0?1/Math.sqrt(i.headSize):i.scale,x=me(i.headSize),$=i.headSize/x,v=12,S={x:Math.ceil(p/v),y:Math.ceil(i.sequenceLength/v),z:i.batchSize*i.numHeads},T=[{type:12,data:i.sequenceLength},{type:12,data:$},{type:12,data:p},{type:12,data:i.numHeads},{type:12,data:i.headSize},{type:1,data:g},{type:12,data:a},{type:12,data:i.kvSequenceLength},{type:12,data:y}],A=u&&n&&k.size(n.dims)>0,C=["type","type"];A&&C.push("type"),o&&C.push("type"),d&&C.push("type"),l&&C.push("type");let P=[{dims:m,dataType:t.dataType,gpuDataType:0}];u&&P.push({dims:_,dataType:t.dataType,gpuDataType:0});let D=R=>{let H=E("q",t.dataType,t.dims,x),L=E("key",r.dataType,r.dims,x),re=[H,L];if(A){let te=E("past_key",n.dataType,n.dims,x);re.push(te)}o&&re.push(E("attention_bias",o.dataType,o.dims));let V=d?E("seq_lens",d.dataType,d.dims):void 0;V&&re.push(V);let K=l?E("total_sequence_length_input",l.dataType,l.dims):void 0;K&&re.push(K);let we=M("output",t.dataType,m),j=[we];u&&j.push(M("present_key",t.dataType,_,x));let Q=Ee(1,x),ie=[{name:"M",type:"u32"},{name:"K",type:"u32"},{name:"N",type:"u32"},{name:"num_heads",type:"u32"},{name:"head_size",type:"u32"},{name:"alpha",type:"f32"},{name:"past_sequence_length",type:"u32"},{name:"kv_sequence_length",type:"u32"},{name:"n_reps",type:"u32"}];return`
  const TILE_SIZE = ${v}u;

  var<workgroup> tileQ: array<${H.type.storage}, ${v*v}>;
  var<workgroup> tileK: array<${H.type.storage}, ${v*v}>;
  ${R.registerUniforms(ie).declareVariables(...re,...j)}
  ${R.mainStart([v,v,1])}
    // x holds the N and y holds the M
    let headIdx = workgroup_id.z % uniforms.num_heads;
    let kvHeadIdx = ${y===1?"headIdx":"headIdx / uniforms.n_reps"};
    let kv_num_heads = ${y===1?"uniforms.num_heads":"uniforms.num_heads / uniforms.n_reps"};
    let batchIdx = workgroup_id.z / uniforms.num_heads;
    let m = workgroup_id.y * TILE_SIZE;
    let n = workgroup_id.x * TILE_SIZE;
    let sequence_length = uniforms.M;
    var total_sequence_length = uniforms.N;
    ${co(V,K,!0)}
    let absKvHeadIdx = batchIdx * kv_num_heads + kvHeadIdx;
    let qOffset = workgroup_id.z * uniforms.M * uniforms.K + m * uniforms.K;
    ${A&&u?"let pastKeyOffset = absKvHeadIdx * uniforms.past_sequence_length * uniforms.K;":""};
    let kOffset = absKvHeadIdx * uniforms.kv_sequence_length * uniforms.K;
    ${u?"let presentKeyOffset = absKvHeadIdx * uniforms.N * uniforms.K;":""}
    var value = ${Q}(0);
    for (var w: u32 = 0u; w < uniforms.K; w += TILE_SIZE) {
      if (global_id.y < uniforms.M && w + local_id.x < uniforms.K) {
        tileQ[TILE_SIZE * local_id.y + local_id.x] = q[qOffset + local_id.y * uniforms.K + w + local_id.x];
      }
      if (n + local_id.y < uniforms.N && w + local_id.x < uniforms.K) {
        var idx = TILE_SIZE * local_id.y + local_id.x;
      ${(()=>A&&u?`
              if (n + local_id.y < past_sequence_length) {
                tileK[idx] = past_key[pastKeyOffset + (n + local_id.y) * uniforms.K + w + local_id.x];
              } else if (n + local_id.y - past_sequence_length < uniforms.kv_sequence_length) {
                tileK[idx] = key[kOffset + (n + local_id.y - past_sequence_length) * uniforms.K + w + local_id.x];
              }`:`
          if (n + local_id.y < uniforms.kv_sequence_length) {
            tileK[idx] = key[kOffset + (n + local_id.y) * uniforms.K + w + local_id.x];
          }`)()}
      ${u?`if (n + local_id.y < present_sequence_length) {
        present_key[presentKeyOffset + (n + local_id.y) * uniforms.K + w + local_id.x] = tileK[idx];
      }`:""}
      }
      workgroupBarrier();

      for (var k: u32 = 0u; k < TILE_SIZE && w+k < uniforms.K; k++) {
          value += ${Q}(tileQ[TILE_SIZE * local_id.y + k] * tileK[TILE_SIZE * local_id.x + k]);
      }

      workgroupBarrier();
    }

    if (global_id.y < uniforms.M && global_id.x < total_sequence_length) {
      let headOffset = workgroup_id.z * uniforms.M * uniforms.N;
      let outputIdx = headOffset + global_id.y * uniforms.N + global_id.x;
      var sum: f32 = ${(()=>{switch(x){case 1:return"value";case 2:return"value.x + value.y";case 4:return"value.x + value.y + value.z + value.w";default:throw new Error(`Unsupported components: ${x}`)}})()};
        output[outputIdx] = ${we.type.value} (sum * uniforms.alpha) + ${o?"attention_bias[outputIdx]":"0.0"};
    }
  }`};return{name:"AttentionProbs",shaderCache:{hint:`${x};${o!==void 0};${n!==void 0};${e}`,inputDependencies:C},getRunData:()=>({outputs:P,dispatchGroup:S,programUniforms:T}),getShaderSource:D}},Um=(e,t,r,n,o,i,a=void 0,d=void 0)=>{let l=i+o.kvSequenceLength,p=o.nReps?o.nReps:1,m=o.vHiddenSize*p,u=e>1&&n,h=o.kvNumHeads?o.kvNumHeads:o.numHeads,_=u?[o.batchSize,h,l,o.headSize]:void 0,y=[o.batchSize,o.sequenceLength,m],g=12,x={x:Math.ceil(o.vHeadSize/g),y:Math.ceil(o.sequenceLength/g),z:o.batchSize*o.numHeads},$=[{type:12,data:o.sequenceLength},{type:12,data:l},{type:12,data:o.vHeadSize},{type:12,data:o.numHeads},{type:12,data:o.headSize},{type:12,data:m},{type:12,data:i},{type:12,data:o.kvSequenceLength},{type:12,data:p}],v=u&&n&&k.size(n.dims)>0,S=["type","type"];v&&S.push("type"),a&&S.push("type"),d&&S.push("type");let T=[{dims:y,dataType:t.dataType,gpuDataType:0}];u&&T.push({dims:_,dataType:t.dataType,gpuDataType:0});let A=C=>{let P=E("probs",t.dataType,t.dims),D=E("v",r.dataType,r.dims),R=[P,D];v&&R.push(E("past_value",n.dataType,n.dims));let H=a?E("seq_lens",a.dataType,a.dims):void 0;a&&R.push(H);let L=d?E("total_sequence_length_input",d.dataType,d.dims):void 0;d&&R.push(L);let V=[M("output",t.dataType,y)];u&&V.push(M("present_value",t.dataType,_));let K=[{name:"M",type:"u32"},{name:"K",type:"u32"},{name:"N",type:"u32"},{name:"num_heads",type:"u32"},{name:"head_size",type:"u32"},{name:"v_hidden_size",type:"u32"},{name:"past_sequence_length",type:"u32"},{name:"kv_sequence_length",type:"u32"},{name:"n_reps",type:"u32"}];return`
  const TILE_SIZE = ${g}u;
  var<workgroup> tileQ: array<${P.type.value}, ${g*g}>;
  var<workgroup> tileV: array<${P.type.value}, ${g*g}>;
  ${C.registerUniforms(K).declareVariables(...R,...V)}
  ${C.mainStart([g,g,1])}
   let headIdx = workgroup_id.z % uniforms.num_heads;
   let batchIdx = workgroup_id.z / uniforms.num_heads;
   let kvHeadIdx = ${p===1?"headIdx":"headIdx / uniforms.n_reps"};
   let kv_num_heads = ${p===1?"uniforms.num_heads":"uniforms.num_heads / uniforms.n_reps"};
   let m = global_id.y;
   let n = global_id.x;
   let sequence_length = uniforms.M;
   var total_sequence_length = uniforms.K;
   ${co(H,L,!0)}
   let offsetA = workgroup_id.z * uniforms.M * uniforms.K + m * uniforms.K;
   let absKvHeadIdx = batchIdx * kv_num_heads + kvHeadIdx; // kvHeadIdx is relative to the batch
   ${v&&u?"let pastValueOffset = absKvHeadIdx * uniforms.N * uniforms.past_sequence_length + n;":""};
   let vOffset = absKvHeadIdx * uniforms.N * uniforms.kv_sequence_length + n;
   ${u?"let presentValueOffset = absKvHeadIdx * uniforms.N * uniforms.K + n;":""}
   var value = ${P.type.storage}(0);
   for (var w: u32 = 0u; w < uniforms.K; w += TILE_SIZE) {
      if (m < uniforms.M && w + local_id.x < uniforms.K) {
        tileQ[TILE_SIZE * local_id.y + local_id.x] = probs[offsetA + w + local_id.x];
      }
      if (n < uniforms.N && w + local_id.y < uniforms.K) {
        var idx = TILE_SIZE * local_id.y + local_id.x;
        ${(()=>v&&u?`
        if (w + local_id.y < past_sequence_length) {
          tileV[idx] = past_value[pastValueOffset + (w + local_id.y) * uniforms.N];
        } else if (w + local_id.y - past_sequence_length < uniforms.kv_sequence_length) {
          tileV[idx] = v[vOffset + (w + local_id.y - past_sequence_length) * uniforms.N];
        }
      `:`
            if (w + local_id.y < uniforms.kv_sequence_length) {
              tileV[idx] = v[vOffset + (w + local_id.y) * uniforms.N];
            }`)()}
        ${u?`
            if (w + local_id.y < present_sequence_length) {
          present_value[presentValueOffset + (w + local_id.y) * uniforms.N] = tileV[idx];
        }`:""}
      }
     workgroupBarrier();
     for (var k: u32 = 0u; k < TILE_SIZE && w+k < total_sequence_length; k++) {
       value += tileQ[TILE_SIZE * local_id.y + k] * tileV[TILE_SIZE * k + local_id.x];
     }
     workgroupBarrier();
   }

   // we need to transpose output from BNSH_v to BSND_v
   if (m < uniforms.M && n < uniforms.N) {
     let outputIdx = batchIdx * uniforms.M * uniforms.v_hidden_size + m * uniforms.v_hidden_size
       + headIdx * uniforms.N + n;
     output[outputIdx] = value;
   }
  }`};return{name:"AttentionScore",shaderCache:{hint:`${n!==void 0};${e}`,inputDependencies:S},getRunData:()=>({outputs:T,dispatchGroup:x,programUniforms:$}),getShaderSource:A}},Ut=(e,t,r,n,o,i,a,d,l,p,m=void 0,u=void 0)=>{let h=Math.min(e.outputCount,1+(a?1:0)+(d?1:0)),_=h>1?p.pastSequenceLength:0,y=_+p.kvSequenceLength,g=l&&k.size(l.dims)>0?l:void 0,x=[t,r];h>1&&a&&k.size(a.dims)>0&&x.push(a),g&&x.push(g),m&&x.push(m),u&&x.push(u);let $=e.compute(Rm(h,t,r,a,g,p,_,m,u),{inputs:x,outputs:h>1?[-1,1]:[-1]})[0];e.compute(Mm($,p.batchSize,p.numHeads,_,p.sequenceLength,y,m,u),{inputs:m&&u?[$,m,u]:[$],outputs:[]});let v=[$,n];h>1&&d&&k.size(d.dims)>0&&v.push(d),m&&v.push(m),u&&v.push(u),e.compute(Um(h,$,n,d,p,_,m,u),{inputs:v,outputs:h>1?[0,2]:[0]})},Nm=(e,t)=>{let r=[t.batchSize,t.numHeads,t.sequenceLength,t.headSize],n=t.sequenceLength,o=t.inputHiddenSize,i=t.headSize,a=12,d={x:Math.ceil(t.headSize/a),y:Math.ceil(t.sequenceLength/a),z:t.batchSize*t.numHeads},l=[e.inputs[0],e.inputs[1],e.inputs[2]],p=[{type:12,data:n},{type:12,data:o},{type:12,data:i},{type:12,data:t.numHeads},{type:12,data:t.headSize},{type:12,data:t.hiddenSize},{type:12,data:t.hiddenSize+t.hiddenSize+t.vHiddenSize}],m=u=>{let h=M("output_q",l[0].dataType,r),_=M("output_k",l[0].dataType,r),y=M("output_v",l[0].dataType,r),g=E("input",l[0].dataType,l[0].dims),x=E("weight",l[1].dataType,l[1].dims),$=E("bias",l[2].dataType,l[2].dims),v=g.type.storage,S=[{name:"M",type:"u32"},{name:"K",type:"u32"},{name:"N",type:"u32"},{name:"num_heads",type:"u32"},{name:"head_size",type:"u32"},{name:"hidden_size",type:"u32"},{name:"ldb",type:"u32"}];return`
  const TILE_SIZE = ${a}u;
  var<workgroup> tileInput: array<${v}, ${a*a}>;
  var<workgroup> tileWeightQ: array<${v}, ${a*a}>;
  var<workgroup> tileWeightK: array<${v}, ${a*a}>;
  var<workgroup> tileWeightV: array<${v}, ${a*a}>;
  ${u.registerUniforms(S).declareVariables(g,x,$,h,_,y)}
  ${u.mainStart([a,a,1])}
    let batchIndex = workgroup_id.z / uniforms.num_heads;
    let headNumber = workgroup_id.z % uniforms.num_heads;
    let m = global_id.y;
    let n = global_id.x;

    let inputOffset = batchIndex * (uniforms.M * uniforms.K) + m * uniforms.K;
    let biasOffsetQ = headNumber * uniforms.head_size;
    let biasOffsetK = uniforms.hidden_size + biasOffsetQ;
    let biasOffsetV = uniforms.hidden_size + biasOffsetK;

    var valueQ = ${v}(0);
    var valueK = ${v}(0);
    var valueV = ${v}(0);
    for (var w: u32 = 0u; w < uniforms.K; w += TILE_SIZE) {
      if (m < uniforms.M && w + local_id.x < uniforms.K) {
        tileInput[TILE_SIZE * local_id.y + local_id.x] = input[inputOffset + w + local_id.x];
      }
      if (n < uniforms.N && w + local_id.y < uniforms.K) {
        let offset = n + (w + local_id.y) * uniforms.ldb;
        tileWeightQ[TILE_SIZE * local_id.y + local_id.x] = weight[biasOffsetQ + offset];
        tileWeightK[TILE_SIZE * local_id.y + local_id.x] = weight[biasOffsetK + offset];
        tileWeightV[TILE_SIZE * local_id.y + local_id.x] = weight[biasOffsetV + offset];
      }
      workgroupBarrier();
      for (var k: u32 = 0u; k<TILE_SIZE && w+k < uniforms.K; k++) {
        let inputTileOffset = TILE_SIZE * local_id.y + k;
        let weightTileOffset = TILE_SIZE * k + local_id.x;
        valueQ += tileInput[inputTileOffset] * tileWeightQ[weightTileOffset];
        valueK += tileInput[inputTileOffset] * tileWeightK[weightTileOffset];
        valueV += tileInput[inputTileOffset] * tileWeightV[weightTileOffset];
      }

      workgroupBarrier();
    }

    let headOffset = (m * uniforms.N + n) % uniforms.head_size;
    valueQ += bias[headOffset + biasOffsetQ];
    valueK += bias[headOffset + biasOffsetK];
    valueV += bias[headOffset + biasOffsetV];

    let offset = workgroup_id.z * uniforms.M * uniforms.N;
    if (m < uniforms.M && n < uniforms.N) {
      let outputIdx = offset + m * uniforms.N + n;
      output_q[outputIdx] = valueQ;
      output_k[outputIdx] = valueK;
      output_v[outputIdx] = valueV;
    }
  }`};return e.compute({name:"AttentionPrepare",shaderCache:{inputDependencies:["type","type","type"]},getRunData:()=>({outputs:[{dims:r,dataType:e.inputs[0].dataType,gpuDataType:0},{dims:r,dataType:e.inputs[0].dataType,gpuDataType:0},{dims:r,dataType:e.inputs[0].dataType,gpuDataType:0}],dispatchGroup:d,programUniforms:p}),getShaderSource:m},{inputs:l,outputs:[-1,-1,-1]})},Ps=(e,t)=>{let r=Bm(e.inputs,t),[n,o,i]=Nm(e,r);return Ut(e,n,o,i,e.inputs[4],void 0,void 0,void 0,e.inputs[5],r)}});var Vm,Wm,Lm,zs,Os=U(()=>{"use strict";Le();J();ne();xe();ae();Vm=(e,t)=>{if(!e||e.length!==5)throw new Error("BatchNormalization requires 5 inputs");let r=(n,o,i)=>{let a=o.length;if(a!==n.length)throw new Error(`${i}: num dimensions != ${a}`);o.forEach((d,l)=>{if(d!==n[l])throw new Error(`${i}: dim[${l}] do not match`)})};if(e[0].dims.length>1){let n=t.format==="NHWC"?t.spatial?e[0].dims.slice(-1):e[0].dims.slice(-1).concat(e[0].dims.slice(1,e[0].dims.length-1)):e[0].dims.slice(1,t.spatial?2:void 0);r(e[1].dims,n,"Invalid input scale"),r(e[2].dims,n,"Invalid input B"),r(e[3].dims,n,"Invalid input mean"),r(e[4].dims,n,"Invalid input var")}else r(e[1].dims,[1],"Invalid input scale"),r(e[2].dims,[1],"Invalid input B"),r(e[3].dims,[1],"Invalid input mean"),r(e[4].dims,[1],"Invalid input var")},Wm=(e,t)=>{let{epsilon:r,spatial:n,format:o}=t,i=e[0].dims,a=n?me(i[i.length-1]):1,d=o==="NHWC"&&i.length>1?a:1,l=k.size(i)/a,p=n,m=p?i.length:i,u=E("x",e[0].dataType,e[0].dims,a),h=E("scale",e[1].dataType,e[1].dims,d),_=E("bias",e[2].dataType,e[2].dims,d),y=E("inputMean",e[3].dataType,e[3].dims,d),g=E("inputVar",e[4].dataType,e[4].dims,d),x=M("y",e[0].dataType,m,a),$=()=>{let S="";if(n)S=`let cOffset = ${i.length===1?"0u":o==="NHWC"?`outputIndices[${i.length-1}] / ${a}`:"outputIndices[1]"};`;else if(o==="NCHW")S=`
            ${x.indicesSet("outputIndices","0","0")}
            let cOffset = ${x.indicesToOffset("outputIndices")};`;else{S=`var cIndices = ${h.type.indices}(0);
                       cIndices[0] = outputIndices[${i.length-1}];`;for(let T=1;T<h.rank;T++)S+=`cIndices[${T}] = outputIndices[${T}];`;S+=`let cOffset = ${h.indicesToOffset("cIndices")};`}return S},v=S=>`
  const epsilon = ${r};
  ${S.registerUniform("outputSize","u32").declareVariables(u,h,_,y,g,x)}
  ${S.mainStart()}
  ${S.guardAgainstOutOfBoundsWorkgroupSizes("uniforms.outputSize")}
    var outputIndices = ${x.offsetToIndices(`global_idx * ${a}`)};
    ${$()}
    let scale = ${h.getByOffset("cOffset")};
    let bias = ${_.getByOffset("cOffset")};
    let inputMean = ${y.getByOffset("cOffset")};
    let inputVar = ${g.getByOffset("cOffset")};
    let x = ${u.getByOffset("global_idx")};
    let value = (x - inputMean) * inverseSqrt(inputVar + epsilon) * scale + bias;
    ${x.setByOffset("global_idx","value")}
  }`;return{name:"BatchNormalization",shaderCache:{hint:`${t.epsilon}_${t.format}_${n}_${a}`,inputDependencies:p?["rank","type","type","type","type"]:void 0},getShaderSource:v,getRunData:()=>({outputs:[{dims:e[0].dims,dataType:e[0].dataType}],dispatchGroup:{x:Math.ceil(l/64)},programUniforms:p?[{type:12,data:l},...N(i)]:[{type:12,data:l}]})}},Lm=e=>ee(e),zs=(e,t)=>{let{inputs:r,outputCount:n}=e,o=Lm({...t,outputCount:n});if(_e.webgpu.validateInputContent&&Vm(r,o),t.trainingMode)throw new Error("BatchNormalization trainingMode is not supported yet.");e.compute(Wm(r,o))}});var Gm,Hm,Ds,Bs=U(()=>{"use strict";ne();ae();Gm=e=>{if(e[0].dims.length!==3)throw new Error("input should have 3 dimensions");if(![320,640,1280].includes(e[0].dims[2]))throw new Error("number of channels should be 320, 640 or 1280");if(e[1].dims.length!==1)throw new Error("bias is expected to have 1 dimensions");if(e[0].dims[2]!==e[1].dims[0])throw new Error("last dimension of input and bias are not the same")},Hm=e=>{let t=e[0].dims,r=e[0].dims[2],n=k.size(t)/4,o=e[0].dataType,i=E("input",o,t,4),a=E("bias",o,[r],4),d=E("residual",o,t,4),l=M("output",o,t,4);return{name:"BiasAdd",getRunData:()=>({outputs:[{dims:t,dataType:e[0].dataType}],dispatchGroup:{x:Math.ceil(n/64)}}),getShaderSource:m=>`
  const channels = ${r}u / 4;
  ${m.declareVariables(i,a,d,l)}

  ${m.mainStart()}
    ${m.guardAgainstOutOfBoundsWorkgroupSizes(n)}
    let value = ${i.getByOffset("global_idx")}
      + ${a.getByOffset("global_idx % channels")} + ${d.getByOffset("global_idx")};
    ${l.setByOffset("global_idx","value")}
  }`}},Ds=e=>{Gm(e.inputs),e.compute(Hm(e.inputs))}});var Fm,fe,Ms,Rs,Us,Ns,Vs,Ws,Ls,Gs,Hs,qm,Fs,qs,Ks,js,Qt,Ys,Fr,Zs,Qs,Xs,Js,eu,tu,ru,nu,ou,iu,au,su,uu,du,lu,cu,pu,mu,po,mo,fu,hu,gu,Km,jm,bu,qr=U(()=>{"use strict";J();ne();xe();ae();Fm=(e,t,r,n,o,i,a)=>{let d=Math.ceil(t/4),l="";typeof o=="string"?l=`${o}(a)`:l=o("a");let p=E("inputData",r,[d],4),m=M("outputData",n,[d],4),u=[{name:"vec_size",type:"u32"}];return a&&u.push(...a),`
      ${e.registerUniforms(u).declareVariables(p,m)}

  ${i??""}

  ${e.mainStart()}
    ${e.guardAgainstOutOfBoundsWorkgroupSizes("uniforms.vec_size")}

    let a = ${p.getByOffset("global_idx")};
    ${m.setByOffset("global_idx",l)}
  }`},fe=(e,t,r,n,o,i=e.dataType,a,d)=>{let l=[{type:12,data:Math.ceil(k.size(e.dims)/4)}];return a&&l.push(...a),{name:t,shaderCache:{hint:o,inputDependencies:["type"]},getShaderSource:p=>Fm(p,k.size(e.dims),e.dataType,i,r,n,d),getRunData:p=>({outputs:[{dims:e.dims,dataType:i}],dispatchGroup:{x:Math.ceil(k.size(p[0].dims)/64/4)},programUniforms:l})}},Ms=e=>{e.compute(fe(e.inputs[0],"Abs","abs"))},Rs=e=>{e.compute(fe(e.inputs[0],"Acos","acos"))},Us=e=>{e.compute(fe(e.inputs[0],"Acosh","acosh"))},Ns=e=>{e.compute(fe(e.inputs[0],"Asin","asin"))},Vs=e=>{e.compute(fe(e.inputs[0],"Asinh","asinh"))},Ws=e=>{e.compute(fe(e.inputs[0],"Atan","atan"))},Ls=e=>{e.compute(fe(e.inputs[0],"Atanh","atanh"))},Gs=e=>ee(e),Hs=(e,t)=>{let r;switch(t.to){case 10:r="vec4<f16>";break;case 1:r="vec4<f32>";break;case 12:r="vec4<u32>";break;case 6:r="vec4<i32>";break;case 9:r="vec4<bool>";break;default:throw new RangeError(`not supported type (specified in attribute 'to' from 'Cast' operator): ${t.to}`)}e.compute(fe(e.inputs[0],"Cast",r,void 0,t.cacheKey,t.to))},qm=e=>{let t,r,n=e.length>=2&&e[1].data!==0,o=e.length>=3&&e[2].data!==0;switch(e[0].dataType){case 1:t=n?e[1].getFloat32Array()[0]:-34028234663852886e22,r=o?e[2].getFloat32Array()[0]:34028234663852886e22;break;case 10:t=n?e[1].getUint16Array()[0]:64511,r=o?e[2].getUint16Array()[0]:31743;break;default:throw new Error("Unsupport data type")}return ee({min:t,max:r})},Fs=(e,t)=>{let r=t||qm(e.inputs),n=Ee(e.inputs[0].dataType);e.compute(fe(e.inputs[0],"Clip",o=>`clamp(${o}, vec4<${n}>(uniforms.min), vec4<${n}>(uniforms.max))`,void 0,r.cacheKey,void 0,[{type:e.inputs[0].dataType,data:r.min},{type:e.inputs[0].dataType,data:r.max}],[{name:"min",type:n},{name:"max",type:n}]),{inputs:[0]})},qs=e=>{e.compute(fe(e.inputs[0],"Ceil","ceil"))},Ks=e=>{e.compute(fe(e.inputs[0],"Cos","cos"))},js=e=>{e.compute(fe(e.inputs[0],"Cosh","cosh"))},Qt=e=>ee(e),Ys=(e,t)=>{let r=Ee(e.inputs[0].dataType);e.compute(fe(e.inputs[0],"Elu",n=>`elu_vf32(${n})`,`
  const elu_alpha_ = ${r}(${t.alpha});

  fn elu_f32(a: ${r}) -> ${r} {
  return select((exp(a) - 1.0) * elu_alpha_, a, a >= 0.0);
  }

  fn elu_vf32(v: vec4<${r}>) -> vec4<${r}> {
  return vec4(elu_f32(v.x), elu_f32(v.y), elu_f32(v.z), elu_f32(v.w));
  }`,t.cacheKey))},Fr=(e="f32")=>`
const r0: ${e} = 0.3275911;
const r1: ${e} = 0.254829592;
const r2: ${e} = -0.284496736;
const r3: ${e} = 1.421413741;
const r4: ${e} = -1.453152027;
const r5: ${e} = 1.061405429;

fn erf_vf32(v: vec4<${e}>) -> vec4<${e}> {
  let absv = abs(v);
  let x = 1.0 / (1.0 + r0 * absv);
  return sign(v) * (1.0 - ((((r5 * x + r4) * x + r3) * x + r2) * x + r1) * x * exp(-absv * absv));
}`,Zs=e=>{let t=Ee(e.inputs[0].dataType);e.compute(fe(e.inputs[0],"Erf",r=>`erf_vf32(${r})`,Fr(t)))},Qs=e=>{e.compute(fe(e.inputs[0],"Exp","exp"))},Xs=e=>{e.compute(fe(e.inputs[0],"Floor","floor"))},Js=e=>{let t=Ee(e.inputs[0].dataType);e.compute(fe(e.inputs[0],"Gelu",r=>`0.5 * ${r} * (1.0 + erf_vf32(${r} * 0.7071067811865475))`,Fr(t)))},eu=(e,t)=>{let r=Ee(e.inputs[0].dataType);e.compute(fe(e.inputs[0],"LeakyRelu",n=>`select(leaky_relu_alpha_ * ${n}, ${n}, ${n} >= vec4<${r}>(0.0))`,`const leaky_relu_alpha_ = ${r}(${t.alpha});`,t.cacheKey))},tu=e=>{e.compute(fe(e.inputs[0],"Not",t=>`!${t}`))},ru=e=>{e.compute(fe(e.inputs[0],"Neg",t=>`-${t}`))},nu=e=>{e.compute(fe(e.inputs[0],"Reciprocal",t=>`1.0/${t}`))},ou=e=>{let t=Ee(e.inputs[0].dataType);e.compute(fe(e.inputs[0],"Relu",r=>`select(vec4<${t}>(0.0), ${r}, ${r} > vec4<${t}>(0.0))`))},iu=e=>{e.compute(fe(e.inputs[0],"Sigmoid",t=>`(1.0 / (1.0 + exp(-${t})))`))},au=e=>ee(e),su=(e,t)=>{let r=Ee(e.inputs[0].dataType);e.compute(fe(e.inputs[0],"HardSigmoid",n=>`max(vec4<${r}>(0.0), min(vec4<${r}>(1.0), ${t.alpha} * ${n} + vec4<${r}>(${t.beta})))`,void 0,t.cacheKey))},uu=e=>{e.compute(fe(e.inputs[0],"Sin","sin"))},du=e=>{e.compute(fe(e.inputs[0],"Sinh","sinh"))},lu=e=>{e.compute(fe(e.inputs[0],"Sqrt","sqrt"))},cu=e=>{e.compute(fe(e.inputs[0],"Tan","tan"))},pu=e=>`sign(${e}) * (1 - exp(-2 * abs(${e}))) / (1 + exp(-2 * abs(${e})))`,mu=e=>{e.compute(fe(e.inputs[0],"Tanh",pu))},po=(e="f32")=>`
const fast_gelu_a: ${e} = 0.5;
const fast_gelu_b: ${e} = 0.7978845608028654;
const fast_gelu_c: ${e} = 0.035677408136300125;

fn tanh_v(v: vec4<${e}>) -> vec4<${e}> {
  return ${pu("v")};
}
`,mo=e=>`(fast_gelu_a + fast_gelu_a * tanh_v(${e} * (fast_gelu_c * ${e} * ${e} + fast_gelu_b))) * ${e}`,fu=e=>{let t=Ee(e.inputs[0].dataType);e.compute(fe(e.inputs[0],"FastGelu",mo,po(t),void 0,e.inputs[0].dataType))},hu=(e,t)=>{let r=Ee(e.inputs[0].dataType);return e.compute(fe(e.inputs[0],"ThresholdedRelu",n=>`select(vec4<${r}>(0.0), ${n}, ${n} > thresholded_relu_alpha_)`,`const thresholded_relu_alpha_ = vec4<${r}>(${t.alpha});`,t.cacheKey)),0},gu=e=>{e.compute(fe(e.inputs[0],"Log","log"))},Km=(e,t)=>`
const alpha = vec4<${e}>(${t});
const one = ${e}(1.0);
const zero = ${e}(0.0);

fn quick_gelu_impl(x: vec4<${e}>) -> vec4<${e}> {
  let v = x *alpha;
  var x1 : vec4<${e}>;
  for (var i = 0; i < 4; i = i + 1) {
    if (v[i] >= zero) {
      x1[i] = one / (one + exp(-v[i]));
    } else {
      x1[i] = one - one / (one + exp(v[i]));
    }
  }
  return x * x1;
}
`,jm=e=>`quick_gelu_impl(${e})`,bu=(e,t)=>{let r=Ee(e.inputs[0].dataType);e.compute(fe(e.inputs[0],"QuickGelu",jm,Km(r,t.alpha),t.cacheKey,e.inputs[0].dataType))}});var Ym,Zm,_u,wu=U(()=>{"use strict";ne();ae();qr();Ym=e=>{if(e[0].dims.length!==3)throw new Error("input should have 3 dimensions");if(![2560,5120,10240].includes(e[0].dims[2]))throw new Error("hidden state should be 2560, 5120 or 10240");if(e[1].dims.length!==1)throw new Error("bias is expected to have 1 dimensions");if(e[0].dims[2]!==e[1].dims[0])throw new Error("last dimension of input and bias are not the same")},Zm=e=>{let t=e[0].dims.slice();t[2]=t[2]/2;let r=E("input",e[0].dataType,e[0].dims,4),n=E("bias",e[0].dataType,[e[0].dims[2]],4),o=M("output",e[0].dataType,t,4),i=k.size(t)/4,a=ye(e[0].dataType);return{name:"BiasSplitGelu",getRunData:()=>({outputs:[{dims:t,dataType:e[0].dataType}],dispatchGroup:{x:Math.ceil(i/64)}}),getShaderSource:l=>`
  const M_SQRT2 = sqrt(2.0);
  const halfChannels = ${e[0].dims[2]/4/2}u;

  ${l.declareVariables(r,n,o)}

  ${Fr(a)}

  ${l.mainStart()}
    ${l.guardAgainstOutOfBoundsWorkgroupSizes(i)}
    let biasIdx = global_idx % halfChannels;
    let batchIndex = global_idx / halfChannels;
    let inputOffset = biasIdx + batchIndex * halfChannels * 2;
    let valueLeft = input[inputOffset] + bias[biasIdx];
    let valueRight = input[inputOffset + halfChannels] + bias[biasIdx + halfChannels];
    let geluRight = valueRight * 0.5 * (erf_vf32(valueRight / M_SQRT2) + 1);

    ${o.setByOffset("global_idx","valueLeft * geluRight")}
  }`}},_u=e=>{Ym(e.inputs),e.compute(Zm(e.inputs))}});var Qm,Xm,at,vu,$u,xu,Su,Tu,Iu,Cu,Au,ku,Eu,Pu=U(()=>{"use strict";J();ne();ae();Qm=(e,t,r,n,o,i,a,d,l,p,m,u)=>{let h,_;typeof d=="string"?h=_=(v,S)=>`${d}((${v}),(${S}))`:typeof d=="function"?h=_=d:(h=d.scalar,_=d.vector);let y=M("outputData",m,n.length,4),g=E("aData",l,t.length,4),x=E("bData",p,r.length,4),$;if(o)if(i){let v=k.size(t)===1,S=k.size(r)===1,T=t.length>0&&t[t.length-1]%4===0,A=r.length>0&&r[r.length-1]%4===0;v||S?$=y.setByOffset("global_idx",_(v?`${g.type.value}(${g.getByOffset("0")}.x)`:g.getByOffset("global_idx"),S?`${x.type.value}(${x.getByOffset("0")}.x)`:x.getByOffset("global_idx"))):$=`
            let outputIndices = ${y.offsetToIndices("global_idx * 4u")};
            let offsetA = ${g.broadcastedIndicesToOffset("outputIndices",y)};
            let offsetB = ${x.broadcastedIndicesToOffset("outputIndices",y)};
            ${y.setByOffset("global_idx",_(a||T?g.getByOffset("offsetA / 4u"):`${g.type.value}(${g.getByOffset("offsetA / 4u")}[offsetA % 4u])`,a||A?x.getByOffset("offsetB / 4u"):`${x.type.value}(${x.getByOffset("offsetB / 4u")}[offsetB % 4u])`))}
          `}else $=y.setByOffset("global_idx",_(g.getByOffset("global_idx"),x.getByOffset("global_idx")));else{if(!i)throw new Error("no necessary to use scalar implementation for element-wise binary op implementation.");let v=(S,T,A="")=>{let C=`aData[indexA${T}][componentA${T}]`,P=`bData[indexB${T}][componentB${T}]`;return`
            let outputIndices${T} = ${y.offsetToIndices(`global_idx * 4u + ${T}u`)};
            let offsetA${T} = ${g.broadcastedIndicesToOffset(`outputIndices${T}`,y)};
            let offsetB${T} = ${x.broadcastedIndicesToOffset(`outputIndices${T}`,y)};
            let indexA${T} = offsetA${T} / 4u;
            let indexB${T} = offsetB${T} / 4u;
            let componentA${T} = offsetA${T} % 4u;
            let componentB${T} = offsetB${T} % 4u;
            ${S}[${T}] = ${A}(${h(C,P)});
          `};m===9?$=`
            var data = vec4<u32>(0);
            ${v("data",0,"u32")}
            ${v("data",1,"u32")}
            ${v("data",2,"u32")}
            ${v("data",3,"u32")}
            outputData[global_idx] = dot(vec4<u32>(0x1, 0x100, 0x10000, 0x1000000), vec4<u32>(data));`:$=`
            ${v("outputData[global_idx]",0)}
            ${v("outputData[global_idx]",1)}
            ${v("outputData[global_idx]",2)}
            ${v("outputData[global_idx]",3)}
          `}return`
        ${e.registerUniform("vec_size","u32").declareVariables(g,x,y)}

        ${u??""}

        ${e.mainStart()}
        ${e.guardAgainstOutOfBoundsWorkgroupSizes("uniforms.vec_size")}
        ${$}
      }`},Xm=(e,t,r,n,o,i,a=r.dataType)=>{let d=r.dims.map(g=>Number(g)??1),l=n.dims.map(g=>Number(g)??1),p=!k.areEqual(d,l),m=d,u=k.size(d),h=!1,_=!1,y=[p];if(p){let g=tt.calcShape(d,l,!1);if(!g)throw new Error("Can't perform binary op on the given tensors");m=g.slice(),u=k.size(m);let x=k.size(d)===1,$=k.size(l)===1,v=d.length>0&&d[d.length-1]%4===0,S=l.length>0&&l[l.length-1]%4===0;y.push(x),y.push($),y.push(v),y.push(S);let T=1;for(let A=1;A<m.length;A++){let C=d[d.length-A],P=l[l.length-A];if(C===P)T*=C;else break}T%4===0?(_=!0,h=!0):(x||$||v||S)&&(h=!0)}else h=!0;return y.push(h),{name:e,shaderCache:{hint:t+y.map(g=>g.toString()).join("_"),inputDependencies:["rank","rank"]},getShaderSource:g=>Qm(g,d,l,m,h,p,_,o,r.dataType,n.dataType,a,i),getRunData:()=>({outputs:[{dims:m,dataType:a}],dispatchGroup:{x:Math.ceil(u/64/4)},programUniforms:[{type:12,data:Math.ceil(k.size(m)/4)},...N(d,l,m)]})}},at=(e,t,r,n,o,i)=>{e.compute(Xm(t,o??"",e.inputs[0],e.inputs[1],r,n,i))},vu=e=>{at(e,"Add",(t,r)=>`${t}+${r}`)},$u=e=>{at(e,"Div",(t,r)=>`${t}/${r}`)},xu=e=>{at(e,"Equal",{scalar:(t,r)=>`u32(${t}==${r})`,vector:(t,r)=>`vec4<u32>(${t}==${r})`},void 0,void 0,9)},Su=e=>{at(e,"Mul",(t,r)=>`${t}*${r}`)},Tu=e=>{let t=E("input",e.inputs[0].dataType,e.inputs[0].dims).type.value;at(e,"Pow",{scalar:(n,o)=>`pow_custom(${n},${o})`,vector:(n,o)=>`pow_vector_custom(${n},${o})`},`
    fn pow_custom(a : ${t}, b : ${t}) -> ${t} {
      if (b == ${t}(0.0)) {
        return ${t}(1.0);
      } else if (a < ${t}(0.0) && f32(b) != floor(f32(b))) {
        return ${t}(pow(f32(a), f32(b))); // NaN
      }
      return select(sign(a), ${t}(1.0), round(f32(abs(b) % ${t}(2.0))) != 1.0) * ${t}(${t==="i32"?"round":""}(pow(f32(abs(a)), f32(b))));
    }
    fn pow_vector_custom(a : vec4<${t}>, b : vec4<${t}>) -> vec4<${t}> {
      // TODO: implement vectorized pow
      return vec4<${t}>(pow_custom(a.x, b.x), pow_custom(a.y, b.y), pow_custom(a.z, b.z), pow_custom(a.w, b.w));
    }
      `)},Iu=e=>{at(e,"Sub",(t,r)=>`${t}-${r}`)},Cu=e=>{at(e,"Greater",{scalar:(t,r)=>`u32(${t}>${r})`,vector:(t,r)=>`vec4<u32>(${t}>${r})`},void 0,void 0,9)},Au=e=>{at(e,"Less",{scalar:(t,r)=>`u32(${t}<${r})`,vector:(t,r)=>`vec4<u32>(${t}<${r})`},void 0,void 0,9)},ku=e=>{at(e,"GreaterOrEqual",{scalar:(t,r)=>`u32(${t}>=${r})`,vector:(t,r)=>`vec4<u32>(${t}>=${r})`},void 0,void 0,9)},Eu=e=>{at(e,"LessOrEqual",{scalar:(t,r)=>`u32(${t}<=${r})`,vector:(t,r)=>`vec4<u32>(${t}<=${r})`},void 0,void 0,9)}});var ef,tf,rf,nf,zu,Ou,Du=U(()=>{"use strict";J();ne();xe();ae();ef=(e,t)=>{if(!e||e.length<1)throw new Error("too few inputs");let r=0,n=e[r],o=n.dataType,i=n.dims.length;e.forEach((a,d)=>{if(d!==r){if(a.dataType!==o)throw new Error("input tensors should be one type");if(a.dims.length!==i)throw new Error("input tensors should have the same shape");a.dims.forEach((l,p)=>{if(p!==t&&l!==n.dims[p])throw new Error("non concat dimensions must match")})}})},tf=(e,t)=>`
  fn calculateInputIndex(index: u32) -> u32 {
    let sizeInConcatAxis = array<u32, ${e}u>(${t});
    for (var i: u32 = 0u; i < ${e}; i += 1u ) {
      if (index < sizeInConcatAxis[i]) {
        return i;
      }
    }
    return ${e}u;
  }`,rf=(e,t)=>{let r=e.length,n=[];for(let o=0;o<r;++o){let i=t.setByOffset("global_idx",e[o].getByIndices("indices"));r===1?n.push(i):o===0?n.push(`if (inputIndex == ${o}u) { ${i} }`):o===r-1?n.push(`else { ${i} }`):n.push(`else if (inputIndex == ${o}) { ${i} }`)}return n.join(`
`)},nf=(e,t,r,n)=>{let o=k.size(r),i=new Array(e.length),a=new Array(e.length),d=0,l=[],p=[],m=[{type:12,data:o}];for(let g=0;g<e.length;++g)d+=e[g].dims[t],i[g]=d,p.push(e[g].dims.length),a[g]=E(`input${g}`,n,p[g]),l.push("rank"),m.push({type:12,data:i[g]});for(let g=0;g<e.length;++g)m.push(...N(e[g].dims));m.push(...N(r));let u=M("output",n,r.length),h=u.indicesGet("indices",t),_=Array.from(Array(i.length).keys()).map(g=>`uniforms.sizeInConcatAxis${g}`).join(","),y=g=>`

  ${(()=>{g.registerUniform("outputSize","u32");for(let x=0;x<e.length;x++)g.registerUniform(`sizeInConcatAxis${x}`,"u32");return g.declareVariables(...a,u)})()}

  ${tf(i.length,_)}

  ${g.mainStart()}
    ${g.guardAgainstOutOfBoundsWorkgroupSizes("uniforms.outputSize")}

    var indices = ${u.offsetToIndices("global_idx")};

    let inputIndex = calculateInputIndex(${h});
    if (inputIndex != 0u) {
      let sizeInConcatAxis = array<u32, ${i.length}u>(${_});
      ${h} -= sizeInConcatAxis[inputIndex - 1u];
    }

    ${rf(a,u)}
  }`;return{name:"Concat",shaderCache:{hint:`${t}`,inputDependencies:l},getRunData:()=>({outputs:[{dims:r,dataType:n}],dispatchGroup:{x:Math.ceil(o/64)},programUniforms:m}),getShaderSource:y}},zu=(e,t)=>{let r=e.inputs,n=r[0].dims,o=k.normalizeAxis(t.axis,n.length);ef(r,o);let i=n.slice();i[o]=r.reduce((d,l)=>d+(l.dims.length>o?l.dims[o]:0),0);let a=r.filter(d=>k.size(d.dims)>0);e.compute(nf(a,o,i,r[0].dataType),{inputs:a})},Ou=e=>ee({axis:e.axis})});var Ke,je,Ye,Kr,yt=U(()=>{"use strict";J();ne();Ke=(e,t,r="f32")=>{switch(e.activation){case"Relu":return`value = max(value, ${t}(0.0));`;case"Sigmoid":return`value = (${t}(1.0) / (${t}(1.0) + exp(-value)));`;case"Clip":return`value = clamp(value, ${t}(${r}(uniforms.clip_min)), ${t}(${r}(uniforms.clip_max)));`;case"HardSigmoid":return`value = max(${t}(0.0), min(${t}(1.0), ${r}(uniforms.alpha) * value + ${r}(uniforms.beta)));`;case"LeakyRelu":return`value = select(${r}(uniforms.alpha) * value, value, value >= ${t}(0.0));`;case"Tanh":return`let e2x = exp(-2.0 * abs(value));
              value = sign(value) * (1.0 - e2x) / (1.0 + e2x);
        `;case"":return"";default:throw new Error(`Unsupported activation ${e.activation}`)}},je=(e,t)=>{e.activation==="Clip"?t.push({type:1,data:e.clipMax},{type:1,data:e.clipMin}):e.activation==="HardSigmoid"?t.push({type:1,data:e.alpha},{type:1,data:e.beta}):e.activation==="LeakyRelu"&&t.push({type:1,data:e.alpha})},Ye=(e,t)=>{e.activation==="Clip"?t.push({name:"clip_max",type:"f32"},{name:"clip_min",type:"f32"}):e.activation==="HardSigmoid"?t.push({name:"alpha",type:"f32"},{name:"beta",type:"f32"}):e.activation==="LeakyRelu"&&t.push({name:"alpha",type:"f32"})},Kr=e=>{let t=e?.activation||"";if(t==="HardSigmoid"){let[r,n]=e?.activation_params||[.2,.5];return{activation:t,alpha:r,beta:n}}else if(t==="Clip"){let[r,n]=e?.activation_params||[Ja,es];return{activation:t,clipMax:n,clipMin:r}}else if(t==="LeakyRelu"){let[r]=e?.activation_params||[.01];return{activation:t,alpha:r}}return{activation:t}}});var Ae,Bu,jr=U(()=>{"use strict";Ae=(e,t)=>{switch(e){case 1:return t;case 2:return`vec2<${t}>`;case 3:return`vec3<${t}>`;case 4:return`vec4<${t}>`;default:throw new Error(`${e}-component is not supported.`)}},Bu=e=>`
      ${e?"value = value + getBiasByOutputCoords(coords);":""}
      `});var Mu,Ru=U(()=>{"use strict";Mu=e=>`
fn getIndexFromCoords4D(coords : vec4<i32>, shape : vec4<i32>) -> i32 {
  return dot(coords, vec4<i32>(
      shape.y * shape.z * shape.w, shape.z * shape.w, shape.w, 1));
}
fn getOutputIndexFromCoords(coords : vec4<i32>) -> i32 {
  return dot(coords, vec4<i32>(
    i32(${e}.x), i32(${e}.y), i32(${e}.z), 1));
}
`});var Xt,Yr,Zr=U(()=>{"use strict";J();ne();ae();yt();Xt=(e,t,r,n,o)=>{let i=n-r;return`
      ${Array.from({length:r}).map((a,d)=>`
      if (${q(t.shape,d,t.rank)} != 1) {
        ${t.indicesSet(e,d,q(o,d+i,n))}
      } else {
        ${t.indicesSet(e,d,0)}
      }`).join("")}
`},Yr=(e,t,r,n,o=!1,i)=>{let a=e[0].dims,d=e[1].dims,l=a[a.length-2],p=d[d.length-1],m=a[a.length-1],u=me(p),h=me(m),_=me(l),y=k.size(r)/u/_,g=e.length>2,x=n?n.slice(0,-2):r.slice(0,-2),v=[k.size(x),l,p],S=[{type:12,data:y},{type:12,data:l},{type:12,data:p},{type:12,data:m}];je(t,S),S.push(...N(x,a,d)),g&&S.push(...N(e[2].dims)),S.push(...N(v));let T=A=>{let C=Wr("batch_dims",e[0].dataType,x.length),P=E("a",e[0].dataType,a.length,h),D=E("b",e[1].dataType,d.length,u),R=M("output",e[0].dataType,v.length,u),H=ye(R.type.tensor),L=Ke(t,R.type.value,H),re=[P,D],V="";if(g){let j=o?u:1;re.push(E("bias",e[2].dataType,e[2].dims.length,j)),V=`${o?`value += bias[col / ${j}];`:`value += ${R.type.value}(bias[row + i]);`}`}let K=[{name:"output_size",type:"u32"},{name:"M",type:"u32"},{name:"N",type:"u32"},{name:"K",type:"u32"}];Ye(t,K);let we=()=>{let j=`var a_data: ${P.type.value};`;for(let Q=0;Q<h;Q++)j+=`
              let b_data${Q} = b[(b_offset + (k + ${Q}) * uniforms.N + col) / ${u}];`;for(let Q=0;Q<_;Q++){j+=`a_data = a[(a_offset + (row + ${Q}) * uniforms.K + k) / ${h}];`;for(let ie=0;ie<h;ie++)j+=`
            values[${Q}] = fma(${D.type.value}(a_data${h===1?"":`[${ie}]`}), b_data${ie}, values[${Q}]);
`}return j};return`
  ${A.registerUniforms(K).registerInternalVariables(C).declareVariables(...re,R)}
  ${A.mainStart()}
    ${A.guardAgainstOutOfBoundsWorkgroupSizes("uniforms.output_size")}
    let col = (global_idx % (uniforms.N / ${u})) * ${u};
    var index1 = global_idx / (uniforms.N / ${u});
    let stride1 = uniforms.M / ${_};
    let row = (index1 % stride1) * ${_};
    let batch = index1 / stride1;

    ${r.length===2?"":`let batch_indices = ${C.offsetToIndices("batch")};`}

    var a_indices: ${P.type.indices};
    ${Xt("a_indices",P,P.rank-2,C.rank,"batch_indices")}
    ${P.indicesSet("a_indices",P.rank-2,0)}
    ${P.indicesSet("a_indices",P.rank-1,0)}
    let a_offset = ${P.indicesToOffset("a_indices")};

    var b_indices: ${D.type.indices};
    ${Xt("b_indices",D,D.rank-2,C.rank,"batch_indices")}
    ${D.indicesSet("b_indices",D.rank-2,0)}
    ${D.indicesSet("b_indices",D.rank-1,0)}
    let b_offset = ${D.indicesToOffset("b_indices")};
    var values: array<${R.type.value}, ${_}>;
    for (var k: u32 = 0u; k < uniforms.K; k = k + ${h}) {
      ${we()}
    }
    for (var i = 0u; i < ${_}u; i++) {
      var value = values[i];
      ${V}
      ${L}
      let cur_indices = ${R.type.indices}(batch, row + i, col);
      let offset = ${R.indicesToOffset("cur_indices")};
      ${R.setByOffset(`offset / ${u}`,"value")};
    }
  }
  `};return{name:"MatMulNaive",shaderCache:{hint:`${t.activation};${u};${h};${_};${o}`,inputDependencies:g?["rank","rank","rank"]:["rank","rank"]},getRunData:()=>({outputs:[{dims:i?i(r):r,dataType:e[0].dataType}],dispatchGroup:{x:Math.ceil(y/64)},programUniforms:S}),getShaderSource:T}}});var of,af,fo,Uu,sf,ho,uf,Jt,Qr=U(()=>{"use strict";J();ne();ae();yt();Zr();jr();of=(e,t)=>e?`
        mm_Asub[inputRow][inputCol] = mm_readA(batch,
          kStart + inputRow,
          globalRowStart / innerElementSize + inputCol${t?", batchIndices":""});
        `:`
        mm_Asub[inputRow][inputCol] = mm_readA(batch,
          globalRow + innerRow,
          kStart / innerElementSize + inputCol${t?", batchIndices":""});
        `,af=(e,t)=>e?`
        let ACached0 = mm_Asub[k * innerElementSize][localRow];
        let ACached1 = mm_Asub[k * innerElementSize + 1][localRow];
        let ACached2 = mm_Asub[k * innerElementSize + 2][localRow];
        ${t===3?"":"let ACached3 = mm_Asub[k * innerElementSize + 3][localRow];"}
        for (var i = 0; i < rowPerThread; i = i + 1) {
          acc[i] = BCached0 * ACached0[i] + acc[i];
          acc[i] = BCached1 * ACached1[i] + acc[i];
          acc[i] = BCached2 * ACached2[i] + acc[i];
          ${t===3?"":"acc[i] = BCached3 * ACached3[i] + acc[i];"}
        }`:`
        for (var i = 0; i < rowPerThread; i = i + 1) {
          let ACached = mm_Asub[tileRow + i][k];
          acc[i] = BCached0 * ACached.x + acc[i];
          acc[i] = BCached1 * ACached.y + acc[i];
          acc[i] = BCached2 * ACached.z + acc[i];
          ${t===3?"":"acc[i] = BCached3 * ACached.w + acc[i];"}
        }`,fo=(e,t,r="f32",n,o=!1,i=32,a=!1,d=32)=>{let l=t[1]*e[1],p=t[0]*e[0],m=o?l:i,u=o?i:l,h=m/t[0],_=i/t[1];if(!((o&&h===4&&e[1]===4||!o&&(h===3||h===4))&&m%t[0]===0&&i%t[1]===0&&e[0]===4))throw new Error(`If transposeA ${o} is true, innerElementSize ${h} and workPerThread[1] ${e[1]} must be 4.
      Otherwise, innerElementSize ${h} must be 3 or 4.
  tileAWidth ${m} must be divisible by workgroupSize[0]${t[0]}. tileInner ${i} must be divisible by workgroupSize[1] ${t[1]}. colPerThread ${e[0]} must be 4.`);return`
var<workgroup> mm_Asub: array<array<vec${h}<${r}>, ${m/h}>, ${u}>;
var<workgroup> mm_Bsub: array<array<vec4<${r}>, ${p/e[0]}>, ${i}>;

const rowPerThread = ${e[1]};
const colPerThread = ${e[0]};
const innerElementSize = ${h};
const tileInner = ${i};

@compute @workgroup_size(${t[0]}, ${t[1]}, ${t[2]})
fn main(@builtin(local_invocation_id) localId : vec3<u32>,
        @builtin(global_invocation_id) globalId : vec3<u32>,
        @builtin(workgroup_id) workgroupId : vec3<u32>) {
  let localRow = i32(localId.y);
  let tileRow = localRow * rowPerThread;
  let tileCol = i32(localId.x);

  let globalRow =i32(globalId.y) * rowPerThread;
  let globalCol = i32(globalId.x);
  let batch = ${a?"0":"i32(globalId.z)"};
  ${n?`let batchIndices = ${n.offsetToIndices("u32(batch)")};`:""}
  let globalRowStart = i32(workgroupId.y) * ${l};

  let num_tiles = ${a?`${Math.ceil(d/i)}`:"(uniforms.dim_inner - 1) / tileInner + 1"};
  var kStart = ${a?`i32(globalId.z) * ${d}`:"0"};

  var acc: array<vec4<${r}>, rowPerThread>;

  // Loop over shared dimension.
  let tileRowB = localRow * ${_};
  for (var t = 0; t < num_tiles; t = t + 1) {
      // Load one tile of A into local memory.
      for (var innerRow = 0; innerRow < rowPerThread; innerRow = innerRow + 1) {
          let inputRow = tileRow + innerRow;
          let inputCol = tileCol;
          ${of(o,n)}
      }

      // Load one tile of B into local memory.
      for (var innerRow = 0; innerRow < ${_}; innerRow = innerRow + 1) {
          let inputRow = tileRowB + innerRow;
          let inputCol = tileCol;
          mm_Bsub[inputRow][inputCol] = mm_readB(batch, kStart + inputRow, globalCol${n?", batchIndices":""});
      }
      kStart = kStart + tileInner;
      workgroupBarrier();

      // Compute acc values for a single thread.
      for (var k = 0; k < tileInner / innerElementSize; k = k + 1) {
          let BCached0 = mm_Bsub[k * innerElementSize][tileCol];
          let BCached1 = mm_Bsub[k * innerElementSize + 1][tileCol];
          let BCached2 = mm_Bsub[k * innerElementSize + 2][tileCol];
          ${h===3?"":"let BCached3 = mm_Bsub[k * innerElementSize + 3][tileCol];"}

          ${af(o,h)}
      }

      workgroupBarrier();
  }

  for (var innerRow = 0; innerRow < rowPerThread; innerRow = innerRow + 1) {
      mm_write(batch, globalRow + innerRow, globalCol, acc[innerRow]);
  }
}`},Uu=(e,t)=>e?`
            mm_Asub[inputRow][inputCol] = mm_readA(batch,
              kStart + inputRow,
              globalRowStart + inputCol${t?", batchIndices":""});
            `:`
            mm_Asub[inputRow][inputCol] = mm_readA(batch,
              globalRowStart + inputRow,
              kStart + inputCol${t?", batchIndices":""});
            `,sf=e=>e?"let ACached = mm_Asub[k][tileRow + innerRow];":"let ACached = mm_Asub[tileRow + innerRow][k];",ho=(e,t,r="f32",n,o=!1,i=32,a=!1,d=32,l=!1)=>{let p=e[1]*t[1],m=e[0]*t[0],u=o?p:i,h=o?i:p;if(!(h%t[1]===0&&u%t[0]===0&&i%t[1]===0))throw new Error(`tileAHight ${h} must be divisible by workgroupSize[1]${t[1]}, tileAWidth ${u} must be divisible by workgroupSize[0]${t[0]}, tileInner ${i} must be divisible by workgroupSize[1]${t[1]}`);let _=h/t[1],y=u/t[0],g=i/t[1],x=l?`
    let localRow = i32(localId.y);
    let localCol = i32(localId.x);
    let globalRowStart = i32(workgroupId.y) * ${p};
    let globalColStart = i32(workgroupId.x) * ${m};

    // Loop over shared dimension.
    for (var t = 0; t < num_tiles; t = t + 1) {
      // Load one tile of A into local memory.
      for (var inputRow = localRow; inputRow < ${h}; inputRow = inputRow + ${t[1]}) {
        for (var inputCol = localCol; inputCol < ${u}; inputCol = inputCol + ${t[0]}) {
          ${Uu(o,n)}
        }
      }
      // Load one tile of B into local memory.
      for (var inputRow = localRow; inputRow < ${i}; inputRow = inputRow + ${t[1]}) {
            for (var inputCol = localCol; inputCol < ${m}; inputCol = inputCol + ${t[0]}) {
          mm_Bsub[inputRow][inputCol] = mm_readB(batch,
            kStart + inputRow,
            globalColStart + inputCol${n?", batchIndices":""});
        }
      }
      kStart = kStart + tileInner;
      workgroupBarrier();

      // Compute acc values for a single thread.
      var BCached : array<${r}, colPerThread>;
      for (var k = 0; k < tileInner; k = k + 1) {
        for (var inner = 0; inner < colPerThread; inner = inner + 1) {
          BCached[inner] = mm_Bsub[k][localCol + inner * ${t[0]}];
        }
        for (var innerRow = 0; innerRow < rowPerThread; innerRow = innerRow + 1) {
          let ACached = ${o?`mm_Asub[k][localRow + innerRow * ${t[1]}];`:`mm_Asub[localRow + innerRow * ${t[1]}][k];`}
          for (var innerCol = 0; innerCol < colPerThread; innerCol = innerCol + 1) {
            acc[innerRow][innerCol] = acc[innerRow][innerCol] +
                ACached * BCached[innerCol];
          }
        }
      }
      workgroupBarrier();
    }
    for (var innerRow = 0; innerRow < rowPerThread; innerRow = innerRow + 1) {
      let gRow = globalRowStart + localRow + innerRow * ${t[1]};
      for (var innerCol = 0; innerCol < colPerThread; innerCol = innerCol + 1) {
        let gCol = globalColStart + localCol + innerCol * ${t[0]};
        mm_write(batch, gRow, gCol, acc[innerRow][innerCol]);
      }
    }
    `:`
let tileRow = i32(localId.y) * rowPerThread;
let tileCol = i32(localId.x) * colPerThread;

let globalRow = i32(globalId.y) * rowPerThread;
let globalCol = i32(globalId.x) * colPerThread;
let globalRowStart = i32(workgroupId.y) * ${p};

let tileRowA = i32(localId.y) * ${_};
let tileColA = i32(localId.x) * ${y};
let tileRowB = i32(localId.y) * ${g};
// Loop over shared dimension.
for (var t = 0; t < num_tiles; t = t + 1) {
  // Load one tile of A into local memory.
  for (var innerRow = 0; innerRow < ${_}; innerRow = innerRow + 1) {
    for (var innerCol = 0; innerCol < ${y}; innerCol = innerCol + 1) {
      let inputRow = tileRowA + innerRow;
      let inputCol = tileColA + innerCol;
      ${Uu(o,n)}
    }
  }

  // Load one tile of B into local memory.
  for (var innerRow = 0; innerRow < ${g}; innerRow = innerRow + 1) {
    for (var innerCol = 0; innerCol < colPerThread; innerCol = innerCol + 1) {
      let inputRow = tileRowB + innerRow;
      let inputCol = tileCol + innerCol;
      mm_Bsub[inputRow][inputCol] = mm_readB(batch,
        kStart + inputRow,
        globalCol + innerCol${n?", batchIndices":""});
    }
  }
  kStart = kStart + tileInner;
  workgroupBarrier();

  // Compute acc values for a single thread.
  var BCached : array<${r}, colPerThread>;
  for (var k = 0; k < tileInner; k = k + 1) {
    for (var inner = 0; inner < colPerThread; inner = inner + 1) {
      BCached[inner] = mm_Bsub[k][tileCol + inner];
    }

    for (var innerRow = 0; innerRow < rowPerThread; innerRow = innerRow + 1) {
      ${sf(o)}
      for (var innerCol = 0; innerCol < colPerThread; innerCol = innerCol + 1) {
        acc[innerRow][innerCol] = acc[innerRow][innerCol] + ACached * BCached[innerCol];
      }
    }
  }

  workgroupBarrier();
}

for (var innerRow = 0; innerRow < rowPerThread; innerRow = innerRow + 1) {
  for (var innerCol = 0; innerCol < colPerThread; innerCol = innerCol + 1) {
    mm_write(batch, globalRow + innerRow, globalCol + innerCol,
        acc[innerRow][innerCol]);
  }
}
`;return`
  var<workgroup> mm_Asub : array<array<${r}, ${u}>, ${h}>;
  var<workgroup> mm_Bsub : array<array<${r}, ${m}>, ${i}>;
  const rowPerThread = ${e[1]};
  const colPerThread = ${e[0]};
  const tileInner = ${i};

@compute @workgroup_size(${t[0]}, ${t[1]}, ${t[2]})
fn main(@builtin(local_invocation_id) localId : vec3<u32>,
        @builtin(global_invocation_id) globalId : vec3<u32>,
        @builtin(workgroup_id) workgroupId : vec3<u32>) {
    let batch = ${a?"0":"i32(globalId.z)"};
    ${n?`let batchIndices = ${n.offsetToIndices("u32(batch)")};`:""}
    let num_tiles = ${a?`${Math.ceil(d/i)}`:"(uniforms.dim_inner - 1) / tileInner + 1"};
    var kStart = ${a?`i32(globalId.z) * ${d}`:"0"};

    var acc : array<array<${r}, colPerThread>, rowPerThread>;
    ${x}
  }
`},uf=(e,t,r,n,o=!1)=>{let[i,a,d,l]=n,p=ye(n[0].type.tensor);return`
    fn mm_readA(batch: i32, row: i32, colIn: i32, batchIndices: ${i.type.indices}) -> ${Ae(e,p)} {
      var value = ${Ae(e,p)}(0.0);
      let col = colIn * ${e};
      if(row < uniforms.dim_a_outer && col < uniforms.dim_inner)
      {
        var aIndices: ${a.type.indices};
        ${Xt("aIndices",a,a.rank-2,i.rank,"batchIndices")}
        ${a.indicesSet("aIndices",a.rank-2,"u32(row)")}
        ${a.indicesSet("aIndices",a.rank-1,"u32(colIn)")}
        value = ${a.getByIndices("aIndices")};
      }
      return value;
    }

    fn mm_readB(batch: i32, row: i32, colIn: i32, batchIndices: ${i.type.indices}) -> ${Ae(e,p)} {
      var value = ${Ae(e,p)}(0.0);
      let col = colIn * ${e};
      if(row < uniforms.dim_inner && col < uniforms.dim_b_outer)
      {
        var bIndices: ${d.type.indices};
        ${Xt("bIndices",d,d.rank-2,i.rank,"batchIndices")}
        ${d.indicesSet("bIndices",d.rank-2,"u32(row)")}
        ${d.indicesSet("bIndices",d.rank-1,"u32(colIn)")}
        value = ${d.getByIndices("bIndices")};
      }
      return value;
    }

    fn mm_write(batch: i32, row: i32, colIn: i32, valueIn: ${Ae(e,p)}) {
      let col = colIn * ${e};
      if (row < uniforms.dim_a_outer && col < uniforms.dim_b_outer) {
        var value = valueIn;
        let coords = vec3<i32>(batch, row, colIn);
        ${t?`value = value + ${o?"bias[colIn]":`${Ae(e,p)}(bias[row])`};`:""}
        ${r}
        ${l.setByIndices("vec3<u32>(coords)","value")}
      }
    }
    `},Jt=(e,t,r,n,o=!1,i)=>{let a=e[0].dims,d=e[1].dims,l=a.slice(0,-2),p=d.slice(0,-2),m=n?n.slice(0,-2):r.slice(0,-2),u=k.size(m),h=a[a.length-2],_=a[a.length-1],y=d[d.length-1],g=_%4===0&&y%4===0,x=h<=8?[4,1,1]:[4,4,1],$=[8,8,1],v=[Math.ceil(y/$[0]/x[0]),Math.ceil(h/$[1]/x[1]),Math.ceil(u/$[2]/x[2])],S=g?4:1,T=[...l,h,_/S],A=T.length,C=[...p,_,y/S],P=C.length,D=[u,h,y/S],R=[{type:6,data:h},{type:6,data:y},{type:6,data:_}];je(t,R),R.push(...N(m,T,C));let H=["rank","rank"],L=e.length>2;L&&(R.push(...N(e[2].dims)),H.push("rank")),R.push(...N(D));let re=V=>{let K=m.length,we=Wr("batchDims",e[0].dataType,K,1),j=ye(e[0].dataType),Q=E("a",e[0].dataType,A,S),ie=E("b",e[1].dataType,P,S),te=M("result",e[0].dataType,D.length,S),be=[Q,ie];if(L){let Y=o?S:1;be.push(E("bias",e[2].dataType,e[2].dims.length,Y))}let Oe=[{name:"dim_a_outer",type:"i32"},{name:"dim_b_outer",type:"i32"},{name:"dim_inner",type:"i32"}];Ye(t,Oe);let ve=ye(te.type.tensor),de=Ke(t,te.type.value,ve),W=uf(S,L,de,[we,Q,ie,te],o);return`
  ${V.registerUniforms(Oe).registerInternalVariables(we).declareVariables(...be,te)}
  ${W}
  ${g?fo(x,$,j,we):ho(x,$,j,we)}
                   `};return{name:"MatMul",shaderCache:{hint:`${x};${t.activation};${g};${o}`,inputDependencies:H},getRunData:()=>({outputs:[{dims:i?i(r):r,dataType:e[0].dataType}],dispatchGroup:{x:v[0],y:v[1],z:v[2]},programUniforms:R}),getShaderSource:re}}});var df,Nu,Vu=U(()=>{"use strict";J();et();ae();yt();jr();Ru();Qr();df=(e,t,r,n,o=!1,i,a=4,d=4,l=4,p="f32")=>{let m=H=>{switch(H){case 1:return"resData = x[xIndex];";case 3:return`resData = vec3<${p}>(x[xIndex], x[xIndex + 1], x[xIndex + 2]);`;case 4:return"resData = x[xIndex / 4];";default:throw new Error(`innerElementSize ${H} is not supported.`)}},u=H=>{switch(H){case 1:return"return w[row * i32(uniforms.w_shape[3]) + colIn];";case 4:return"return w[row * i32(uniforms.w_shape[3]) / 4 + colIn];";default:throw new Error(`innerElementSize ${H} is not supported.`)}},h=e?`
    let coord = vec4<i32>(batch, xRow, xCol, xCh);
    `:`
    let coord = vec4<i32>(batch, xCh, xRow, xCol);
    `,_=e?`
    let coords = vec4<i32>(
      batch,
      row / outWidth,
      row % outWidth,
      col);
    `:`
    let coords = vec4<i32>(
      batch,
      row,
      col / outWidth,
      col % outWidth);
    `,y=e?"i32(uniforms.x_shape[1])":"i32(uniforms.x_shape[2])",g=e?"i32(uniforms.x_shape[2])":"i32(uniforms.x_shape[3])",x=e?"row":"col",$=e?"col":"row",v=`
    let inChannels = i32(uniforms.w_shape[2]);
    let outWidth = ${e?"i32(uniforms.result_shape[2])":"i32(uniforms.result_shape[3])"};
    let outRow = ${x} / outWidth;
    let outCol = ${x} % outWidth;

    let WRow = ${$} / (i32(uniforms.w_shape[1]) * inChannels);
    let WCol = ${$} / inChannels % i32(uniforms.w_shape[1]);
    let xRow = outRow * uniforms.stride[0] + uniforms.dilation[0] * WRow - uniforms.pad[0];
    let xCol = outCol * uniforms.stride[1] + uniforms.dilation[1] * WCol - uniforms.pad[1];
    let xCh = ${$} % inChannels;
    var resData = ${Ae(a,p)}(0.0);
    // The bounds checking is always needed since we use it to pad zero for
    // the 'same' padding type.
    if (xRow >= 0 && xRow < ${y} && xCol >= 0 && xCol < ${g}) {
      ${h}
      let xIndex = getIndexFromCoords4D(coord, vec4<i32>(uniforms.x_shape));
      ${m(a)}
    }
    return resData;`,S=e?t&&n?`
    let col = colIn * ${a};
    ${v}`:`
    let col = colIn * ${a};
    if (row < uniforms.dim_a_outer && col < uniforms.dim_inner) {
      ${v}
    }
    return ${Ae(a,p)}(0.0);`:n&&r?`
    let col = colIn * ${a};
    ${v}`:`
    let col = colIn * ${a};
    if (row < uniforms.dim_inner && col < uniforms.dim_b_outer) {
      ${v}
    }
    return ${Ae(a,p)}(0.0);`,T=e?n&&r?u(d):`
    let col = colIn * ${d};
    if (row < uniforms.dim_inner && col < uniforms.dim_b_outer) {
      ${u(d)}
    }
    return ${Ae(d,p)}(0.0);`:`
    let col = colIn * ${d};
    if (row < uniforms.dim_inner && col < uniforms.dim_a_outer) {
      ${u(d)}
    }
    return ${Ae(d,p)}(0.0);`,A=Ae(l,p),C=e?Ae(a,p):Ae(d,p),P=e?Ae(d,p):Ae(a,p),D=Ke(i,A,p);return`
    fn mm_readA(batch: i32, row : i32, colIn : i32) -> ${C} {
      ${e?S:T}
    }

    fn mm_readB(batch: i32, row : i32, colIn : i32) -> ${P} {
      ${e?T:S}
    }

    fn mm_write(batch: i32, row : i32, colIn : i32, valueIn : ${A}) {
      let col = colIn * ${l};
      if (row < uniforms.dim_a_outer && col < uniforms.dim_b_outer)
      {
      var value = valueIn;
      let outWidth = ${e?"i32(uniforms.result_shape[2])":"i32(uniforms.result_shape[3])"};
      ${_}
      ${Bu(o)}
      ${D}
      setOutputAtCoords(coords[0], coords[1], coords[2], coords[3], value);
      }
    }`},Nu=(e,t,r,n,o,i,a,d,l)=>{let p=t.format==="NHWC",m=p?e[0].dims[3]:e[0].dims[1],u=r[0],h=p?r[2]:r[3],_=p?r[1]:r[2],y=p?r[3]:r[1],g=p&&(m%4===0||m%3===0)&&y%4===0,x=p?y:h*_,$=p?h*_:y,v=[8,8,1],S=n<=8?[4,1,1]:[4,4,1],T=[Math.ceil(x/v[0]/S[0]),Math.ceil($/v[1]/S[1]),Math.ceil(u/v[2]/S[2])];se("verbose",()=>`[conv2d_mm_webgpu] dispatch = ${T}`);let A=g?p&&m%4!==0?3:4:1,C=v[1]*S[1],P=v[0]*S[0],D=Math.max(v[0]*A,v[1]),R=n%C===0,H=o%P===0,L=i%D===0,re=g?[A,4,4]:[1,1,1],V=[{type:6,data:n},{type:6,data:o},{type:6,data:i},{type:6,data:[t.pads[0],t.pads[1]]},{type:6,data:t.strides},{type:6,data:t.dilations}];je(t,V),V.push(...N(e[0].dims,e[1].dims));let K=["rank","rank"];a&&(V.push(...N(e[2].dims)),K.push("rank")),V.push(...N(r));let we=j=>{let Q=[{name:"dim_a_outer",type:"i32"},{name:"dim_b_outer",type:"i32"},{name:"dim_inner",type:"i32"},{name:"pad",type:"i32",length:2},{name:"stride",type:"i32",length:2},{name:"dilation",type:"i32",length:2}];Ye(t,Q);let ie=g?4:1,te=ye(e[0].dataType),be=`
      fn setOutputAtIndex(flatIndex : i32, value : ${g?`vec4<${te}>`:te}) {
        result[flatIndex] = ${g?`vec4<${te}>`:te}(value);
      }
      fn setOutputAtCoords(d0 : i32, d1 : i32, d2 : i32, d3 : i32, value : ${g?`vec4<${te}>`:te}) {
        let flatIndex = getOutputIndexFromCoords(vec4<i32>(d0, d1, d2, d3));
        setOutputAtIndex(flatIndex ${g?"/ 4":""}, value);
      }`,Oe=E("x",e[0].dataType,e[0].dims.length,A===3?1:A),ve=E("w",e[1].dataType,e[1].dims.length,ie),de=[Oe,ve],W=M("result",e[0].dataType,r.length,ie);if(a){let Y=E("bias",e[2].dataType,e[2].dims.length,ie);de.push(Y),be+=`
        fn getBiasByOutputCoords(coords : vec4<i32>) -> ${g?`vec4<${te}>`:te} {
          return bias[coords.${p?"w":"y"}${g?"/ 4":""}];
        }`}return`
        ${Mu("uniforms.result_strides")}
        //struct Uniforms { xShape : vec4<i32>, wShape : vec4<i32>, outShape : vec4<i32>,
        //  outShapeStrides: vec3<i32>, filterDims : vec2<i32>, pad : vec2<i32>, stride : vec2<i32>,
        //  dilation : vec2<i32>, dimAOuter : i32, dimBOuter : i32, dimInner : i32 };
        ${j.registerUniforms(Q).declareVariables(...de,W)}
        ${be}
        ${df(p,R,H,L,a,t,re[0],re[1],re[2],te)}
        ${g?fo(S,v,te,void 0,!p,D):ho(S,v,te,void 0,!p,D,!1,void 0,d)}`};return{name:"Conv2DMatMul",shaderCache:{hint:`${t.cacheKey};${A};${g};${R};${H};${L};${C};${P};${D}`,inputDependencies:K},getRunData:()=>({outputs:[{dims:l?l(r):r,dataType:e[0].dataType}],dispatchGroup:{x:T[0],y:T[1],z:T[2]},programUniforms:V}),getShaderSource:we}}});var lf,Wu,Xr,cf,Lu,pf,Gu,Hu,Fu=U(()=>{"use strict";J();et();ne();ae();yt();jr();lf=e=>{let t=1;for(let r=0;r<e.length;r++)t*=e[r];return t},Wu=e=>typeof e=="number"?[e,e,e]:e,Xr=(e,t)=>t<=1?e:e+(e-1)*(t-1),cf=(e,t,r,n=1)=>{let o=Xr(t,n);return Math.floor((e[0]*(r-1)-r+o)/2)},Lu=(e,t,r,n,o)=>{o==null&&(o=cf(e,t[0],n[0]));let i=[0,0,0,r];for(let a=0;a<3;a++)e[a]+2*o>=t[a]&&(i[a]=Math.trunc((e[a]-t[a]+2*o)/n[a]+1));return i},pf=(e,t,r,n,o,i,a,d,l,p)=>{let m,u,h,_;if(e==="VALID"&&(e=0),typeof e=="number"){m={top:e,bottom:e,left:e,right:e,front:e,back:e};let y=Lu([t,r,n,1],[d,l,p],1,[o,i,a],e);u=y[0],h=y[1],_=y[2]}else if(Array.isArray(e)){if(!e.every((g,x,$)=>g===$[0]))throw Error(`Unsupported padding parameter: ${e}`);m={top:e[0],bottom:e[1],left:e[2],right:e[3],front:e[4],back:e[5]};let y=Lu([t,r,n,1],[d,l,p],1,[o,i,a],e[0]);u=y[0],h=y[1],_=y[2]}else if(e==="SAME_UPPER"){u=Math.ceil(t/o),h=Math.ceil(r/i),_=Math.ceil(n/a);let y=(u-1)*o+d-t,g=(h-1)*i+l-r,x=(_-1)*a+p-n,$=Math.floor(y/2),v=y-$,S=Math.floor(g/2),T=g-S,A=Math.floor(x/2),C=x-A;m={top:S,bottom:T,left:A,right:C,front:$,back:v}}else throw Error(`Unknown padding parameter: ${e}`);return{padInfo:m,outDepth:u,outHeight:h,outWidth:_}},Gu=(e,t,r,n,o,i=!1,a="channelsLast")=>{let d,l,p,m,u;if(a==="channelsLast")[d,l,p,m,u]=e;else if(a==="channelsFirst")[d,u,l,p,m]=e;else throw new Error(`Unknown dataFormat ${a}`);let[h,,_,y,g]=t,[x,$,v]=Wu(r),[S,T,A]=Wu(n),C=Xr(_,S),P=Xr(y,T),D=Xr(g,A),{padInfo:R,outDepth:H,outHeight:L,outWidth:re}=pf(o,l,p,m,x,$,v,C,P,D),V=i?h*u:h,K=[0,0,0,0,0];return a==="channelsFirst"?K=[d,V,H,L,re]:a==="channelsLast"&&(K=[d,H,L,re,V]),{batchSize:d,dataFormat:a,inDepth:l,inHeight:p,inWidth:m,inChannels:u,outDepth:H,outHeight:L,outWidth:re,outChannels:V,padInfo:R,strideDepth:x,strideHeight:$,strideWidth:v,filterDepth:_,filterHeight:y,filterWidth:g,effectiveFilterDepth:C,effectiveFilterHeight:P,effectiveFilterWidth:D,dilationDepth:S,dilationHeight:T,dilationWidth:A,inShape:e,outShape:K,filterShape:t}},Hu=(e,t,r,n,o,i)=>{let a=i==="channelsLast",d=a?e[0].dims[3]:e[0].dims[1],l=!1,p=[64,1,1],m={x:r.map((v,S)=>S)},u=[Math.ceil(lf(m.x.map(v=>r[v]))/p[0]),1,1];se("verbose",()=>`[conv3d_naive_webgpu] dispatch = ${u}`);let h=l?a&&d%4!==0?3:4:1,_=k.size(r),y=[{type:12,data:_},{type:12,data:n},{type:12,data:o},{type:12,data:t.strides},{type:12,data:t.dilations}];je(t,y),y.push(...N(e[0].dims,e[1].dims));let g=["rank","rank"],x=e.length===3;x&&(y.push(...N(e[2].dims)),g.push("rank")),y.push(...N(r));let $=v=>{let S=[{name:"output_size",type:"u32"},{name:"filter_dims",type:"u32",length:n.length},{name:"pads",type:"u32",length:o.length},{name:"strides",type:"u32",length:t.strides.length},{name:"dilations",type:"u32",length:t.dilations.length}];Ye(t,S);let T=l?4:1,A=ye(e[0].dataType),C=E("x",e[0].dataType,e[0].dims.length,h===3?1:h),P=E("W",e[1].dataType,e[1].dims.length,T),D=[C,P],R=M("result",e[0].dataType,r.length,T),H="";if(x){let V=E("bias",e[2].dataType,e[2].dims.length,T);D.push(V),H+=`
        fn getBiasByOutputCoords(coords : array<u32, 5>) -> ${l?`vec4<${A}>`:A} {
          return bias[${a?q("coords",4,5):q("coords",1,5)}${l?"/ 4":""}];
        }`}let L=Ae(h,A),re=Ke(t,L,A);return`
            ${H}
            fn getX(d0 : u32, d1 : u32, d2 : u32, d3 : u32, d4 : u32) -> f32 {
              let aIndices = array<u32, 5>(d0, d1, d2, d3, d4);
              return ${C.getByIndices("aIndices")};
            }
            fn getW(d0 : u32, d1 : u32, d2 : u32, d3 : u32, d4 : u32) -> f32 {
              let aIndices = array<u32, 5>(d0, d1, d2, d3, d4);
              return ${P.getByIndices("aIndices")};
            }
          ${v.registerUniforms(S).declareVariables(...D,R)}
          ${v.mainStart()}
          ${v.guardAgainstOutOfBoundsWorkgroupSizes("uniforms.output_size")}
              let coords = ${R.offsetToIndices("global_idx")};
              let batch = ${q("coords",0,C.rank)};
              let d2 = ${a?q("coords",C.rank-1,C.rank):q("coords",1,C.rank)};
              let xFRCCorner = vec3<u32>(${a?q("coords",1,C.rank):q("coords",2,C.rank)},
              ${a?q("coords",2,C.rank):q("coords",3,C.rank)},
              ${a?q("coords",3,C.rank):q("coords",4,C.rank)}) * uniforms.strides - uniforms.pads;
              let xFCorner = xFRCCorner.x;
              let xRCorner = xFRCCorner.y;
              let xCCorner = xFRCCorner.z;
              let xShapeY = ${a?q("uniforms.x_shape",1,C.rank):q("uniforms.x_shape",2,C.rank)};
              let xShapeZ = ${a?q("uniforms.x_shape",2,C.rank):q("uniforms.x_shape",3,C.rank)};
              let xShapeW = ${a?q("uniforms.x_shape",3,C.rank):q("uniforms.x_shape",4,C.rank)};
              let xShapeU = ${a?q("uniforms.x_shape",4,C.rank):q("uniforms.x_shape",1,C.rank)};
              let inputDepthNearestVec4 = (xShapeU / 4) * 4;
              let inputDepthVec4Remainder = xShapeU % 4;

              var value = 0.0;
              for (var wF = 0u; wF < uniforms.filter_dims[0]; wF++) {
                let xF = xFCorner + wF * uniforms.dilations[0];
                if (xF < 0 || xF >= xShapeY) {
                  continue;
                }

                for (var wR = 0u; wR < uniforms.filter_dims[1]; wR++) {
                  let xR = xRCorner + wR * uniforms.dilations[1];
                  if (xR < 0 || xR >= xShapeZ) {
                    continue;
                  }

                  for (var wC = 0u; wC < uniforms.filter_dims[2]; wC++) {
                    let xC = xCCorner + wC * uniforms.dilations[2];
                    if (xC < 0 || xC >= xShapeW) {
                      continue;
                    }

                    for (var d1 = 0u; d1 < inputDepthNearestVec4; d1 += 4) {
                      ${a?`let xValues = vec4<f32>(
                               getX(batch, xF, xR, xC, d1),
                               getX(batch, xF, xR, xC, d1 + 1),
                               getX(batch, xF, xR, xC, d1 + 2),
                               getX(batch, xF, xR, xC, d1 + 3));
                            `:`let xValues = vec4<f32>(
                               getX(batch, d1, xF, xR, xC),
                               getX(batch, d1 + 1, xF, xR, xC),
                               getX(batch, d1 + 2, xF, xR, xC),
                               getX(batch, d1 + 3, xF, xR, xC));
                            `}
                            let wValues = vec4<f32>(
                              getW(d2, d1, wF, wR, wC),
                              getW(d2, d1 + 1, wF, wR, wC),
                              getW(d2, d1 + 2, wF, wR, wC),
                              getW(d2, d1 + 3, wF, wR, wC));
                      value += dot(xValues, wValues);
                    }
                    if (inputDepthVec4Remainder == 1) {
                        ${a?`value += getX(batch, xF, xR, xC, inputDepthNearestVec4)
                          * getW(d2, inputDepthNearestVec4, wF, wR, wC);`:`value += getX(batch, inputDepthNearestVec4, xF, xR, xC)
                          * getW(d2, inputDepthNearestVec4, wF, wR, wC);`}
                    } else if (inputDepthVec4Remainder == 2) {
                      ${a?`let xValues = vec2<f32>(
                        getX(batch, xF, xR, xC, inputDepthNearestVec4),
                        getX(batch, xF, xR, xC, inputDepthNearestVec4 + 1));
                      `:`let xValues = vec2<f32>(
                        getX(batch, inputDepthNearestVec4, xF, xR, xC),
                        getX(batch, inputDepthNearestVec4 + 1, xF, xR, xC));
                    `}
                    let wValues = vec2<f32>(
                      getW(d2, inputDepthNearestVec4, wF, wR, wC),
                      getW(d2, inputDepthNearestVec4 + 1, wF, wR, wC));
                      value += dot(xValues, wValues);
                    } else if (inputDepthVec4Remainder == 3) {
                      ${a?`let xValues = vec3<f32>(
                        getX(batch, xF, xR, xC, inputDepthNearestVec4),
                        getX(batch, xF, xR, xC, inputDepthNearestVec4 + 1),
                        getX(batch, xF, xR, xC, inputDepthNearestVec4 + 2));
                      `:`let xValues = vec3<f32>(
                        getX(batch, inputDepthNearestVec4, xF, xR, xC),
                        getX(batch, inputDepthNearestVec4 + 1, xF, xR, xC),
                        getX(batch, inputDepthNearestVec4 + 2, xF, xR, xC));
                    `}
                    let wValues = vec3<f32>(
                      getW(d2, inputDepthNearestVec4, wF, wR, wC),
                      getW(d2, inputDepthNearestVec4 + 1, wF, wR, wC),
                      getW(d2, inputDepthNearestVec4 + 2, wF, wR, wC));
                      value += dot(xValues, wValues);
                    }
                  }
                }
              }
              ${x?"value = value + getBiasByOutputCoords(coords)":""};
              ${re}
              result[global_idx] = f32(value);
          }`};return{name:"Conv3DNaive",shaderCache:{hint:`${t.cacheKey};${a};${h};${x}`,inputDependencies:g},getRunData:()=>({outputs:[{dims:r,dataType:e[0].dataType}],dispatchGroup:{x:u[0],y:u[1],z:u[2]},programUniforms:y}),getShaderSource:$}}});var qu,Ku,ju=U(()=>{"use strict";J();ne();ae();yt();qu=(e,t,r,n)=>{let o=e.length>2,i=o?"value += b[output_channel];":"",a=e[0].dims,d=e[1].dims,l=t.format==="NHWC",p=l?r[3]:r[1],m=p/t.group,u=l&&m>=4?me(p):1,h=k.size(r)/u,_=[{type:12,data:h},{type:12,data:t.dilations},{type:12,data:[t.strides[0],t.strides[1]]},{type:12,data:[t.pads[0],t.pads[1]]},{type:12,data:m}];je(t,_),_.push(...N(a,[d[0],d[1],d[2],d[3]/u]));let y=o?["rank","rank","rank"]:["rank","rank"];_.push(...N([r[0],r[1],r[2],r[3]/u]));let g=x=>{let $=M("output",e[0].dataType,r.length,u),v=ye($.type.tensor),S=Ke(t,$.type.value,v),T=E("x",e[0].dataType,a.length),A=E("w",e[1].dataType,d.length,u),C=[T,A];o&&C.push(E("b",e[2].dataType,e[2].dims,u));let P=[{name:"output_size",type:"u32"},{name:"dilations",type:"u32",length:t.dilations.length},{name:"strides",type:"u32",length:2},{name:"pads",type:"u32",length:2},{name:"output_channels_per_group",type:"u32"}];Ye(t,P);let D=l?`
      for (var wHeight: u32 = 0u; wHeight < uniforms.w_shape[0]; wHeight++) {
        let xHeight = xRCCorner.x + wHeight * uniforms.dilations[0];

        if (xHeight < 0u || xHeight >= uniforms.x_shape[1]) {
          continue;
        }

        for (var wWidth: u32 = 0u; wWidth < uniforms.w_shape[1]; wWidth++) {
          let xWidth = xRCCorner.y + wWidth * uniforms.dilations[1];
          if (xWidth < 0u || xWidth >= uniforms.x_shape[2]) {
            continue;
          }

          for (var wInChannel: u32 = 0u; wInChannel < uniforms.w_shape[2]; wInChannel++) {
            let input_channel = in_channel_offset + wInChannel;
            let xVal = ${T.get("batch","xHeight","xWidth","input_channel")};
            let wVal = ${A.get("wHeight","wWidth","wInChannel","output_channel")};
            value += xVal * wVal;
          }
        }
      }
      `:`
      for (var wInChannel: u32 = 0u; wInChannel < uniforms.w_shape[1]; wInChannel++) {
        let input_channel = in_channel_offset + wInChannel;
        for (var wHeight: u32 = 0u; wHeight < uniforms.w_shape[2]; wHeight++) {
          let xHeight = xRCCorner.x + wHeight * uniforms.dilations[0];

          if (xHeight < 0u || xHeight >= uniforms.x_shape[2]) {
            continue;
          }

          for (var wWidth: u32 = 0u; wWidth < uniforms.w_shape[3]; wWidth++) {
            let xWidth = xRCCorner.y + wWidth * uniforms.dilations[1];
            if (xWidth < 0u || xWidth >= uniforms.x_shape[3]) {
              continue;
            }

            let xVal = ${T.get("batch","input_channel","xHeight","xWidth")};
            let wVal = ${A.get("output_channel","wInChannel","wHeight","wWidth")};
            value += xVal * wVal;
          }
        }
      }
      `;return`
  ${x.registerUniforms(P).declareVariables(...C,$)}

  ${x.mainStart()}
    ${x.guardAgainstOutOfBoundsWorkgroupSizes("uniforms.output_size")}

    let outputIndices = ${$.offsetToIndices("global_idx")};
    let batch: u32 = outputIndices[0];
    let output_channel: u32 = outputIndices[${l?3:1}];
    let xRCCorner: vec2<u32> = vec2<u32>(outputIndices[${l?1:2}], outputIndices[${l?2:3}]) * uniforms.strides - uniforms.pads;
    let group_id: u32 = output_channel * ${u} / uniforms.output_channels_per_group;
    var in_channel_offset = group_id * uniforms.w_shape[${l?2:1}];

    var value: ${$.type.value} = ${$.type.value}(0);
    ${D}
    ${i}
    ${S}
    ${$.setByOffset("global_idx","value")}
  }`};return{name:"GroupedConv",shaderCache:{hint:`${t.cacheKey}_${u}`,inputDependencies:y},getRunData:()=>({outputs:[{dims:n?n(r):r,dataType:e[0].dataType}],dispatchGroup:{x:Math.ceil(h/64)},programUniforms:_}),getShaderSource:g}},Ku=(e,t,r,n)=>{let o=e.length>2,i=me(r[3]),a=me(r[2]),d=k.size(r)/i/a,l=[e[0].dims[0],e[0].dims[1],e[0].dims[2],e[0].dims[3]/i],p=[e[1].dims[0],e[1].dims[1],e[1].dims[2],e[1].dims[3]/i],m=[r[0],r[1],r[2],r[3]/i],u=[{type:12,data:d},{type:6,data:[t.strides[0],t.strides[1]]},{type:6,data:[t.pads[0],t.pads[1]]}];je(t,u),u.push(...N(l,p,m));let h=(a-1)*t.strides[1]+p[1],_=y=>{let g=M("output",e[0].dataType,m.length,i),x=ye(g.type.tensor),$=Ke(t,g.type.value,x),v=E("x",e[0].dataType,l.length,i),S=E("w",e[1].dataType,p.length,i),T=[v,S];o&&T.push(E("b",e[2].dataType,e[2].dims,i));let A=o?"value += b[output_channel];":"",C=[{name:"output_size",type:"u32"},{name:"strides",type:"i32",length:2},{name:"pads",type:"i32",length:2}];return Ye(t,C),`
  ${y.registerUniforms(C).declareVariables(...T,g)}
  ${y.mainStart()}
    ${y.guardAgainstOutOfBoundsWorkgroupSizes("uniforms.output_size")}
    let width0 = uniforms.output_shape[3];
    let output_channel = global_idx % width0;
    var index1 = global_idx / width0;
    let width1 = uniforms.output_shape[2] / ${a}u;
    let col = (index1 % width1) * ${a}u;
    index1 = index1 / width1;
    let row = index1 % uniforms.output_shape[1];
    let batch = index1 / uniforms.output_shape[1];

    let x_corner = vec2<i32>(i32(row), i32(col)) * uniforms.strides - uniforms.pads;

    var x_vals: array<${v.type.value}, ${h}>;
    var values: array<${g.type.value}, ${a}>;
    let input_channel = output_channel;
    // Use constant instead of uniform can give better performance for w's height/width.
    for (var w_height: u32 = 0u; w_height < ${p[0]}; w_height++) {
      let x_height = x_corner.x + i32(w_height);
      if (x_height >= 0 && u32(x_height) < uniforms.x_shape[1]) {
        for (var i = 0; i < ${h}; i++) {
          let x_width = x_corner.y + i;
          if (x_width >= 0 && u32(x_width) < uniforms.x_shape[2]) {
            x_vals[i] = ${v.get("batch","u32(x_height)","u32(x_width)","input_channel")};
          } else {
            x_vals[i] = ${v.type.value}(0);
          }
        }
        for (var w_width: u32 = 0u; w_width < ${p[1]}; w_width++) {
          let w_val = ${S.get("w_height","w_width","0","output_channel")};
          for (var i = 0u; i < ${a}u; i++) {
            values[i] = fma(x_vals[i * u32(uniforms.strides[1]) + w_width], w_val, values[i]);
          }
        }
      }
    }

    for (var i = 0u; i < ${a}u; i++) {
      var value = values[i];
      ${A}
      ${$}
      ${g.set("batch","row","col + i","output_channel","value")};
    }
  }`};return{name:"GroupedConv-Vectorize",shaderCache:{hint:`${t.cacheKey};${i};${a};${h};${p[0]};${p[1]}`,inputDependencies:o?["rank","rank","type"]:["rank","rank"]},getRunData:()=>({outputs:[{dims:n?n(r):r,dataType:e[0].dataType}],dispatchGroup:{x:Math.ceil(d/64)},programUniforms:u}),getShaderSource:_}}});var mf,go,ff,bo,yo,Yu,hf,gf,_o,Zu=U(()=>{"use strict";ne();Vu();Fu();Qr();ju();yt();Zr();dt();mf=(e,t,r,n,o,i)=>{let a=e[0],d=e.slice(i?1:2,i?3:4),l=d.length,p=t[0],u=t.slice(2).map((y,g)=>y+(y-1)*(r[g]-1)),_=d.map((y,g)=>y+n[g]+n[g+l]).map((y,g)=>Math.floor((y-u[g]+o[g])/o[g]));return _.splice(0,0,a),_.splice(i?3:1,0,p),_},go=[2,3,1,0],ff=(e,t)=>{if(!e||e.length!==2&&e.length!==3)throw new Error("Conv requires 2 or 3 inputs");if(e[0].dims.length>5)throw new Error("greater than 5D is not supported");if(e[0].dims.length!==e[1].dims.length)throw new Error("filter does not have same dimension as input");let r=e[0].dims[t.format==="NHWC"?e[0].dims.length-1:1],n=e[1].dims[1]*t.group;if(r!==n)throw new Error("FILTER_IN_CHANNEL should be equal to DATA_CHANNEL");if(e.length===3&&(e[2].dims.length!==1||e[1].dims[0]!==e[2].dims[0]))throw new Error("invalid bias");let o=e[0].dims.length-2;if(t.dilations.length!==o)throw new Error(`dilations should be ${o}D`);if(t.strides.length!==o)throw new Error(`strides should be ${o}D`);if(t.pads.length!==o*2)throw new Error(`pads should be ${o*2}D`);if(t.kernelShape.length!==0&&t.kernelShape.length!==e[1].dims.length-2)throw new Error("invalid kernel shape")},bo=(e,t)=>{let r=e.kernelShape.slice();r.length<t[1].dims.length-2&&r.push(...Array(t[1].dims.length-2-r.length).fill(0));for(let i=2;i<t[1].dims.length;++i)r[i-2]===0&&(r[i-2]=t[1].dims[i]);let n=e.pads.slice();kt.adjustPadsBasedOnAutoPad(t[0].dims,e.strides,e.dilations,r,n,e.format==="NHWC",e.autoPad);let o=Object.assign({},e);return Object.assign(o,{kernelShape:r,pads:n}),o},yo=e=>{let t=Kr(e),r=e.format,n=["NOTSET","VALID","SAME_UPPER","SAME_LOWER"][e.auto_pad],o=e.dilations,i=e.group,a=e.kernel_shape,d=e.pads,l=e.strides,p=e.w_is_const();return{autoPad:n,format:r,dilations:o,group:i,kernelShape:a,pads:d,strides:l,wIsConst:p,...t,cacheKey:`${e.format};${t.activation};`}},Yu=(e,t,r,n)=>{let o=r.format==="NHWC",i=mf(t[0].dims,t[1].dims,r.dilations,r.pads,r.strides,o);if(r.group!==1){let C=[t[0]];if(o){let D=e.kernelCustomData.wT??e.compute(Pe(t[1],go),{inputs:[1],outputs:[r.wIsConst?-2:-1]})[0];r.wIsConst&&!e.kernelCustomData.wT&&(e.kernelCustomData.wT=D),C.push(D)}else C.push(t[1]);t.length===3&&C.push(t[2]),!e.adapterInfo.isArchitecture("ampere")&&o&&t[1].dims[0]===r.group&&t[1].dims[1]===1&&r.dilations[0]===1&&r.dilations[1]===1?e.compute(Ku(C,r,i,n),{inputs:C}):e.compute(qu(C,r,i,n),{inputs:C});return}let a=t.length===3,d=t[0].dims[o?1:2],l=t[0].dims[o?2:3],p=t[0].dims[o?3:1],m=t[1].dims[2],u=t[1].dims[3],h=i[o?1:2],_=i[o?2:3],y=i[o?3:1],g=o&&m===d&&u===l&&r.pads[0]===0&&r.pads[1]===0;if(g||m===1&&u===1&&r.dilations[0]===1&&r.dilations[1]===1&&r.strides[0]===1&&r.strides[1]===1&&r.pads[0]===0&&r.pads[1]===0){let C=i[0],P,D,R,H=[];if(o){let V=e.kernelCustomData.wT??e.compute(Pe(t[1],go),{inputs:[1],outputs:[r.wIsConst?-2:-1]})[0];if(r.wIsConst&&!e.kernelCustomData.wT&&(e.kernelCustomData.wT=V),g){let K=d*l*p;P=t[0].reshape([1,C,K]),D=V.reshape([1,K,y]),R=[1,C,y]}else P=t[0].reshape([C,d*l,p]),D=V.reshape([1,p,y]),R=[C,h*_,y];H.push(P),H.push(D)}else P=t[0].reshape([C,p,d*l]),D=t[1].reshape([1,y,p]),R=[C,y,h*_],H.push(D),H.push(P);a&&H.push(t[2]);let L=R[2],re=H[0].dims[H[0].dims.length-1];L<8&&re<8?e.compute(Yr(H,r,i,R,o,n),{inputs:H}):e.compute(Jt(H,r,i,R,o,n),{inputs:H});return}let x=!0,$=e.kernelCustomData.wT??e.compute(Pe(t[1],go),{inputs:[1],outputs:[r.wIsConst?-2:-1]})[0];r.wIsConst&&!e.kernelCustomData.wT&&(e.kernelCustomData.wT=$);let v=[t[0],$];a&&v.push(t[2]);let S=o?h*_:y,T=o?y:h*_,A=m*u*p;e.compute(Nu(v,r,i,S,T,A,a,x,n),{inputs:v})},hf=(e,t)=>{let r=t.format==="NHWC",n=[e.inputs[0].reshape(r?[e.inputs[0].dims[0],1,e.inputs[0].dims[1],e.inputs[0].dims[2]]:[e.inputs[0].dims[0],e.inputs[0].dims[1],1,e.inputs[0].dims[2]]),e.inputs[1].reshape([e.inputs[1].dims[0],e.inputs[1].dims[1],1,e.inputs[1].dims[2]])];e.inputs.length===3&&n.push(e.inputs[2]);let o=[0,t.pads[0],0,t.pads[1]],i=[1].concat(t.strides),a=[1].concat(t.dilations),d=[1].concat(t.kernelShape),l=bo({...t,pads:o,strides:i,dilations:a,kernelShape:d},n);Yu(e,n,l,p=>r?[p[0],p[2],p[3]]:[p[0],p[1],p[3]])},gf=(e,t,r)=>{let n=r.format==="NHWC"?"channelsLast":"channelsFirst",o=bo(r,t),i=r.autoPad==="NOTSET"?r.pads:r.autoPad,a=Gu(t[0].dims,t[1].dims,r.strides,r.dilations,i,!1,n);e.compute(Hu(t,o,a.outShape,[a.filterDepth,a.filterHeight,a.filterWidth],[a.padInfo.front,a.padInfo.top,a.padInfo.left],n))},_o=(e,t)=>{if(ff(e.inputs,t),e.inputs[0].dims.length===3)hf(e,t);else if(e.inputs[0].dims.length===5)gf(e,e.inputs,t);else{let r=bo(t,e.inputs);Yu(e,e.inputs,r)}}});var Qu,Xu=U(()=>{"use strict";J();et();ne();ae();Qu=(e,t,r)=>{let n=e.length>2,o=t.outputShape,i=t.format==="NHWC",a=t.group,d=e[1].dims,l=d[2]/a,p=d[3],m=i?me(l):1,u=i?me(p):1,h=i?p===1?m:u:1,_=k.size(o)/u,y=[Math.ceil(_/64),1,1];se("verbose",()=>`[conv2d_backprop_webgpu] dispatch = ${y}`);let g=["rank","rank"],x=[t.strides[0],t.strides[1]],$=[t.kernelShape[i?1:2],t.kernelShape[i?2:3]],v=[t.dilations[0],t.dilations[1]],S=[$[0]+(t.dilations[0]<=1?0:(t.kernelShape[i?1:2]-1)*(t.dilations[0]-1)),$[1]+(t.dilations[1]<=1?0:(t.kernelShape[i?2:3]-1)*(t.dilations[1]-1))],T=[S[0]-1-Math.floor((t.pads[0]+t.pads[2])/2),S[1]-1-Math.floor((t.pads[1]+t.pads[3])/2)],A=[{type:12,data:_},{type:12,data:x},{type:12,data:$},{type:12,data:v},{type:12,data:S},{type:6,data:T},{type:12,data:l},{type:12,data:p},...N(e[0].dims,e[1].dims)];n&&(A.push(...N(e[2].dims)),g.push("rank")),A.push(...N(o));let C=P=>{let D=[{name:"output_size",type:"u32"},{name:"strides",type:"u32",length:x.length},{name:"filter_dims",type:"u32",length:$.length},{name:"dilations",type:"u32",length:$.length},{name:"effective_filter_dims",type:"u32",length:S.length},{name:"pads",type:"i32",length:T.length},{name:"input_channels_per_group",type:"u32"},{name:"output_channels_per_group",type:"u32"}],R=ye(e[0].dataType),H=i?1:2,L=i?2:3,re=i?3:1,V=E("W",e[1].dataType,e[1].dims.length,h),K=E("Dy",e[0].dataType,e[0].dims.length,m),we=[K,V];n&&we.push(E("bias",e[2].dataType,[o[re]].length,u));let j=M("result",e[0].dataType,o.length,u),Q=()=>{let te="";if(m===1)te+=`
        let w_offset = ${V.indicesToOffset(`${V.type.indices}(u32(wRPerm), u32(wCPerm), inputChannel, wOutChannel)`)};
        let wValue = ${V.getByOffset(`w_offset / ${h}`)};
        dotProd = dotProd + xValue * wValue;`;else if(p===1)te+=`
          let wValue = ${V.getByOffset(`${V.indicesToOffset(`${V.type.indices}(u32(wRPerm), u32(wCPerm), inputChannel, wOutChannel)`)} / ${h}`)};
          dotProd = dotProd + dot(xValue, wValue);`;else for(let be=0;be<m;be++)te+=`
            let wValue${be} = ${V.getByOffset(`${V.indicesToOffset(`${V.type.indices}(u32(wRPerm), u32(wCPerm), inputChannel + ${be}, wOutChannel)`)} / ${h}`)};
            dotProd = dotProd + xValue[${be}] * wValue${be};`;return te},ie=`
            let outputIndices = ${j.offsetToIndices(`global_idx * ${u}`)};
            let batch = ${j.indicesGet("outputIndices",0)};
            let d1 = ${j.indicesGet("outputIndices",re)};
            let r = ${j.indicesGet("outputIndices",H)};
            let c = ${j.indicesGet("outputIndices",L)};
            let dyCorner = vec2<i32>(i32(r), i32(c)) - uniforms.pads;
            let dyRCorner = dyCorner.x;
            let dyCCorner = dyCorner.y;
            let groupId = d1 / uniforms.output_channels_per_group;
            let wOutChannel = d1 - groupId * uniforms.output_channels_per_group;
            // Convolve dy(?, ?, d2) with w(:, :, d1, d2) to compute dx(xR, xC, d1).
            // ? = to be determined. : = across all values in that axis.
            var dotProd = ${j.type.value}(0.0);
            var wR: u32 = 0;
            if (uniforms.dilations.x == 1) {
              // Minimum wR >= 0 that satisfies (dyRCorner + wR) % (uniforms.strides.x) == 0
              wR = u32(((dyRCorner + i32(uniforms.strides.x) - 1) / i32(uniforms.strides.x)) * i32(uniforms.strides.x) - dyRCorner);
            }
            for (; wR < uniforms.effective_filter_dims.x; wR = wR + 1) {
              if (wR % uniforms.dilations.x != 0) {
                continue;
              }
              let dyR = (${R}(dyRCorner) + ${R}(wR)) / ${R}(uniforms.strides[0]);
              let wRPerm = uniforms.filter_dims.x - 1 - wR / uniforms.dilations.x;
              if (dyR < 0.0 || dyR >= ${R}(uniforms.Dy_shape[${H}]) || fract(dyR) > 0.0 ||
                  wRPerm < 0) {
                continue;
              }
              let idyR: u32 = u32(dyR);
              var wC: u32 = 0;
              if (uniforms.dilations.y == 1) {
                // Minimum wC >= 0 that satisfies (dyCCorner + wC) % (uniforms.strides.y) == 0
                wC = u32(((dyCCorner + i32(uniforms.strides.y) - 1) / i32(uniforms.strides.y)) * i32(uniforms.strides.y) - dyCCorner);
              }

              for (; wC < uniforms.effective_filter_dims.y; wC = wC + 1) {
                if (wC % uniforms.dilations.y != 0) {
                  continue;
                }
                let dyC = (${R}(dyCCorner) + ${R}(wC)) / ${R}(uniforms.strides.y);
                let wCPerm = uniforms.filter_dims.y - 1 - wC / uniforms.dilations.y;
                if (dyC < 0.0 || dyC >= ${R}(uniforms.Dy_shape[${L}]) ||
                    fract(dyC) > 0.0 || wCPerm < 0) {
                  continue;
                }
                let idyC: u32 = u32(dyC);
                var inputChannel = groupId * uniforms.input_channels_per_group;
                for (var d2: u32 = 0; d2 < uniforms.input_channels_per_group; d2 = d2 + ${m}) {
                  let xValue = ${i?K.getByOffset(`${K.indicesToOffset(`${K.type.indices}(batch, idyR, idyC, inputChannel)`)} / ${m}`):K.get("batch","inputChannel","idyR","idyC")};
                  ${Q()}
                  inputChannel = inputChannel + ${m};
                }
                wC = wC + uniforms.strides.y - 1;
              }
              wR = wR + uniforms.strides[0] - 1;
            }
            let value = dotProd${n?` + bias[d1 / ${u}]`:""};
            ${j.setByOffset("global_idx","value")};
          `;return`
    ${P.registerUniforms(D).declareVariables(...we,j)}
      ${P.mainStart()}
      ${P.guardAgainstOutOfBoundsWorkgroupSizes("uniforms.output_size")};
    ${ie}}`};return{name:"ConvTranspose2D",shaderCache:{hint:`${t.cacheKey};${m}${h}${u}${p===1}`,inputDependencies:g},getRunData:()=>({dispatchGroup:{x:y[0],y:y[1],z:y[2]},outputs:[{dims:r?r(o):o,dataType:e[0].dataType}],programUniforms:A}),getShaderSource:C}}});var bf,yf,_f,Ju,ed,wf,td,vf,rd,nd=U(()=>{"use strict";Xu();yt();dt();bf=(e,t,r,n,o,i)=>(e-1)*t+r+(n-1)*o+1-i,yf=(e,t,r,n,o)=>{let i=Math.floor(e/2);t==="SAME_UPPER"?(r[n]=i,r[o]=e-i):t==="SAME_LOWER"&&(r[n]=e-i,r[o]=i)},_f=(e,t,r,n,o,i,a,d,l,p)=>{let m=e.length-2,u=p.length===0;l.length<m&&l.push(...Array(m-l.length).fill(0));let h=e[0],_=t[d?3:1]*o;for(let y=0,g=e.length-m-(d?1:0);y<m;++y,++g){let x=e[g],$=u?x*a[y]:p[y],v=bf(x,a[y],i[y],t[g],r[y],$);yf(v,n,i,y,y+m),u&&p.push(a[y]*(x-1)+l[y]+(t[g]-1)*r[y]+1-i[y]-i[y+m])}p.splice(0,0,h),p.splice(d?3:1,0,_)},Ju=(e,t)=>{let r=e.kernelShape.slice();if(e.kernelShape.length===0||e.kernelShape.reduce((u,h)=>u*h,1)===0){r.length=0;for(let u=2;u<t[1].dims.length;++u)r.push(t[1].dims[u])}let n=e.format==="NHWC";r.splice(0,0,t[1].dims[0]),r.splice(n?3:1,0,t[1].dims[1]);let o=e.pads.slice(),i=e.outputShape.slice(),a=e.outputPadding.slice(),d=t[0].dims,l=e.dilations.slice();if(l.reduce((u,h)=>u+h,0)===0){let u=t[0].dims.length-2;l=new Array(u).fill(1)}let p=e.strides.slice();if(p.reduce((u,h)=>u+h,0)===0){let u=t[0].dims.length-2;p=new Array(u).fill(1)}_f(d,r,l,e.autoPad,e.group,o,p,n,a,i);let m=Object.assign({},e);return Object.assign(m,{kernelShape:r,pads:o,outputPadding:a,outputShape:i,dilations:l,strides:p}),m},ed=e=>{let t=Kr(e),r=e.format,n=["NOTSET","VALID","SAME_UPPER","SAME_LOWER"][typeof e.autoPad>"u"?0:e.autoPad],o=e.dilations,i=e.group,a=e.kernelShape,d=e.pads,l=e.strides,p=e.wIsConst(),m=e.outputPadding,u=e.outputShape;return{autoPad:n,format:r,dilations:o,group:i,kernelShape:a,outputPadding:m,outputShape:u,pads:d,strides:l,wIsConst:p,...t,cacheKey:`${e.format};${t.activation};`}},wf=(e,t)=>{if(!e||e.length!==2&&e.length!==3)throw new Error("Conv requires 2 or 3 inputs");if(e[0].dims.length!==4&&e[0].dims.length!==3)throw new Error("currently only support 2-dimensional conv");if(e[0].dims.length!==e[1].dims.length)throw new Error("filter does not have same dimension as input");let r=e[0].dims[t.format==="NHWC"?e[0].dims.length-1:1],n=e[1].dims[0];if(r!==n)throw new Error("FILTER_IN_CHANNEL should be equal to DATA_CHANNEL");let o=e[1].dims[1]*t.group;if(e.length===3&&(e[2].dims.length!==1||e[2].dims[0]!==o))throw new Error("invalid bias");let i=e[0].dims.length-2;if(t.dilations.reduce((m,u)=>m+u,0)>0&&t.dilations.length!==i)throw new Error(`dilations should be ${i}D`);if(t.strides.reduce((m,u)=>m+u,0)>0&&t.strides.length!==i)throw new Error(`strides should be ${i}D`);if(t.pads.reduce((m,u)=>m+u,0)>0&&t.pads.length!==i*2)throw new Error(`pads should be ${i*2}D`);if(t.outputPadding.length!==i&&t.outputPadding.length!==0)throw new Error(`output_padding should be ${i}D`);if(t.kernelShape.reduce((m,u)=>m+u,0)>0&&t.kernelShape.length!==0&&t.kernelShape.length!==e[1].dims.length-2)throw new Error("invalid kernel shape");if(t.outputShape.length!==0&&t.outputShape.length!==e[0].dims.length-2)throw new Error("invalid output shape")},td=(e,t,r,n)=>{let o=e.kernelCustomData.wT??e.compute(Pe(t[1],[2,3,0,1]),{inputs:[1],outputs:[r.wIsConst?-2:-1]})[0];r.wIsConst&&!e.kernelCustomData.wT&&(e.kernelCustomData.wT=o);let i=[t[0],o];t.length===3&&i.push(t[2]),e.compute(Qu(i,r,n),{inputs:i})},vf=(e,t)=>{let r=t.format==="NHWC",n=[e.inputs[0].reshape(r?[e.inputs[0].dims[0],1,e.inputs[0].dims[1],e.inputs[0].dims[2]]:[e.inputs[0].dims[0],e.inputs[0].dims[1],1,e.inputs[0].dims[2]]),e.inputs[1].reshape([e.inputs[1].dims[0],e.inputs[1].dims[1],1,e.inputs[1].dims[2]])];e.inputs.length===3&&n.push(e.inputs[2]);let o=t.kernelShape;(o.length===0||o[0]===0)&&(o=[e.inputs[1].dims[2]]);let i=t.dilations;(i.length===0||i[0]===0)&&(i=[1]);let a=t.strides;(a.length===0||a[0]===0)&&(a=[1]);let d=t.pads;d.length===0&&(d=[0,0]),d=[0,d[0],0,d[1]],a=[1].concat(a),i=[1].concat(i),o=[1].concat(o);let l=t.outputPadding;l=[0].concat(l);let p=Ju({...t,pads:d,strides:a,dilations:i,kernelShape:o,outputPadding:l},n);td(e,n,p,m=>r?[m[0],m[2],m[3]]:[m[0],m[1],m[3]])},rd=(e,t)=>{if(wf(e.inputs,t),e.inputs[0].dims.length===3)vf(e,t);else{let r=Ju(t,e.inputs);td(e,e.inputs,r)}}});var $f,od,id,ad=U(()=>{"use strict";J();ne();xe();ae();$f=(e,t,r,n)=>{let o=k.size(t),i=t.length,a=E("input",e,i),d=M("output",e,i),l=r.dataType===6?r.getInt32Array()[0]:Number(r.getBigInt64Array()[0]),p=k.normalizeAxis(l,i),m=u=>{let h=` i32(${a.indicesGet("inputIndices","uniforms.axis")}) `,_=q("uniforms.input_shape","uniforms.axis",i),y=n.reverse?h+(n.exclusive?" + 1":""):"0",g=n.reverse?_:h+(n.exclusive?"":" + 1");return`
                ${u.registerUniform("outputSize","u32").registerUniform("axis","u32").declareVariables(a,d)}
                ${u.mainStart()}
                  ${u.guardAgainstOutOfBoundsWorkgroupSizes("uniforms.outputSize")}
                  var inputIndices = ${d.offsetToIndices("global_idx")};
                  var sum = ${d.type.value}(0);
                  let first : i32 = ${y};
                  let last : i32 = ${g};
                  for (var i : i32 = first; i < last; i++) {
                    ${a.indicesSet("inputIndices","uniforms.axis","u32(i)")};
                    sum = sum + ${a.getByIndices("inputIndices")};
                  }
                  ${d.setByOffset("global_idx","sum")};
                }`};return{name:"CumSum",shaderCache:{hint:n.cacheKey,inputDependencies:["rank"]},getRunData:()=>({outputs:[{dims:t,dataType:e}],dispatchGroup:{x:Math.ceil(o/64)},programUniforms:[{type:12,data:o},{type:12,data:p},...N(t,t)]}),getShaderSource:m}},od=(e,t)=>{let r=e.inputs[0].dims,n=e.inputs[0].dataType,o=e.inputs[1];e.compute($f(n,r,o,t),{inputs:[0]})},id=e=>{let t=e.exclusive===1,r=e.reverse===1;return ee({exclusive:t,reverse:r})}});var xf,Sf,Tf,sd,ud,dd=U(()=>{"use strict";J();ne();xe();ae();xf=e=>{if(!e||e.length!==1)throw new Error("DepthToSpace requires 1 input.");if(e[0].dims.length!==4)throw new Error("DepthToSpace requires 4D input.")},Sf=(e,t,r,n)=>{let o=[];o.push(`fn perm(i: ${n.type.indices}) -> ${r.type.indices} {
    var a: ${r.type.indices};`);for(let i=0;i<t;++i)o.push(r.indicesSet("a",e[i],`i[${i}]`));return o.push("return a;}"),o.join(`
`)},Tf=(e,t)=>{let r,n,o,i,a,d,l=t.format==="NHWC",p=t.blocksize,m=t.mode==="DCR";l?([r,n,o,i]=e.dims,a=m?[r,n,o,p,p,i/p**2]:[r,n,o,i/p**2,p,p],d=m?[0,1,3,2,4,5]:[0,1,4,2,5,3]):([r,n,o,i]=[e.dims[0],e.dims[2],e.dims[3],e.dims[1]],a=m?[r,p,p,i/p**2,n,o]:[r,i/p**2,p,p,n,o],d=m?[0,3,4,1,5,2]:[0,1,4,2,5,3]);let u=e.reshape(a),h=u.dims.length,_=e.dataType,y=E("a",_,h),g=M("output",_,h),x=$=>`
  ${$.registerUniform("output_size","u32").declareVariables(y,g)}

  ${Sf(d,h,y,g)}

  ${$.mainStart()}
    ${$.guardAgainstOutOfBoundsWorkgroupSizes("uniforms.output_size")}

    let indices = ${g.offsetToIndices("global_idx")};
    let aIndices = perm(indices);

    ${g.setByOffset("global_idx",y.getByIndices("aIndices"))}
  }`;return{name:"DepthToSpace",shaderCache:{hint:`${e.dims};${t.blocksize};${t.mode}`,inputDependencies:["rank"]},getRunData:$=>{let v=l?[r,n*p,o*p,i/p**2]:[r,i/p**2,n*p,o*p],S=k.size(v),T=u.dims,A=k.sortBasedOnPerm(T,d);return{outputs:[{dims:v,dataType:$[0].dataType}],dispatchGroup:{x:Math.ceil(S/64)},programUniforms:[{type:12,data:S},...N(T,A)]}},getShaderSource:x}},sd=(e,t)=>{xf(e.inputs),e.compute(Tf(e.inputs[0],t))},ud=e=>ee({blocksize:e.blocksize,mode:e.mode,format:e.format})});var wo,Jr,ld,If,Cf,vo,$o,cd,Af,pd,md,fd=U(()=>{"use strict";J();ne();xe();ae();wo="[a-zA-Z]|\\.\\.\\.",Jr="("+wo+")+",ld="^"+Jr+"$",If="("+Jr+",)*"+Jr,Cf="^"+If+"$",vo=class{constructor(t=-1){this.symbolToIndices=new Map,this.inputIndex=t}addSymbol(t,r){let n=this.symbolToIndices.get(t);n===void 0?n=[r]:n.push(r),this.symbolToIndices.set(t,n)}},$o=class{constructor(t,r){this.equation=r;this.hasEllipsis=!1,this.symbolToInfo=new Map,this.lhs=new Array,this.outputDims=[];let[n,o]=r.includes("->")?r.split("->",2):[r,""];if(!n.match(RegExp(Cf)))throw new Error("Invalid LHS term");if(n.split(",").forEach((d,l)=>{let p=t[l].dims.slice();if(!d.match(RegExp(ld)))throw new Error("Invalid LHS term");let m=this.processTerm(d,!0,p,l);this.lhs.push(m)}),o==="")o+=[...this.symbolToInfo.entries()].filter(([d,l])=>l.count===1||d==="...").map(([d])=>d).join("");else if(!o.match(RegExp(Jr)))throw new Error("Invalid RHS");o.match(RegExp(wo,"g"))?.forEach(d=>{if(d==="...")this.outputDims=this.outputDims.concat(this.ellipsisDims);else{let l=this.symbolToInfo.get(d);if(l===void 0)throw new Error("Invalid RHS symbol");this.outputDims.push(l.dimValue)}}),this.rhs=this.processTerm(o,!1,this.outputDims)}addSymbol(t,r,n){let o=this.symbolToInfo.get(t);if(o!==void 0){if(o.dimValue!==r&&o.count!==1)throw new Error("Dimension mismatch");o.count++,o.inputIndices.push(n)}else o={count:1,dimValue:r,inputIndices:[n]};this.symbolToInfo.set(t,o)}processTerm(t,r,n,o=-1){let i=n.length,a=!1,d=[],l=0;if(!t.match(RegExp(ld))&&!r&&t!=="")throw new Error("Invalid LHS term");let p=t.match(RegExp(wo,"g")),m=new vo(o);return p?.forEach((u,h)=>{if(u==="..."){if(a)throw new Error("Only one ellipsis is allowed per input term");a=!0;let _=i-p.length+1;if(_<0)throw new Error("Ellipsis out of bounds");if(d=n.slice(l,l+_),this.hasEllipsis){if(this.ellipsisDims.length!==d.length||this.ellipsisDims.toString()!==d.toString())throw new Error("Ellipsis dimensions mismatch")}else if(r)this.hasEllipsis=!0,this.ellipsisDims=d;else throw new Error("Ellipsis must be specified in the LHS");for(let y=0;y<d.length;y++){let g=String.fromCharCode("0".charCodeAt(0)+y);m.addSymbol(g,h+y),this.addSymbol(g,n[l++],o)}}else m.addSymbol(u,h+(this.hasEllipsis?this.ellipsisDims.length-1:0)),this.addSymbol(u,n[l++],o)}),m}},cd=e=>e+"_max",Af=(e,t,r,n)=>{let i=e.map(m=>m.length).map((m,u)=>E(`input${u}`,t,m)),a=k.size(n),d=M("output",t,n.length),l=[...r.symbolToInfo.keys()].filter(m=>!r.rhs.symbolToIndices.has(m)),p=m=>{let u=[],h="var prod = 1.0;",_="var sum = 0.0;",y="sum += prod;",g=[],x=[],$=[],v=[],S=r.symbolToInfo.size===r.rhs.symbolToIndices.size;r.symbolToInfo.forEach((A,C)=>{if(r.rhs.symbolToIndices.has(C)){let P=r.rhs.symbolToIndices.get(C)?.[0];P!==void 0&&r.lhs.forEach((D,R)=>{if(A.inputIndices.includes(R)){let H=D.symbolToIndices.get(C);if(H===void 0)throw new Error("Invalid symbol error");H.forEach(L=>{u.push(`${i[R].indicesSet(`input${R}Indices`,L,d.indicesGet("outputIndices",P))}`)})}})}else r.lhs.forEach((P,D)=>{if(A.inputIndices.includes(D)){let R=P.symbolToIndices.get(C);if(R===void 0)throw new Error("Invalid symbol error");R.forEach(H=>{g.push(`${i[D].indicesSet(`input${D}Indices`,H,`${C}`)}`)}),v.push(`prod *= ${i[D].getByIndices(`input${D}Indices`)};`)}}),x.push(`for(var ${C}: u32 = 0; ${C} < uniforms.${cd(C)}; ${C}++) {`),$.push("}")});let T=S?[...u,`let sum = ${i.map((A,C)=>A.getByIndices(`input${C}Indices`)).join(" * ")};`]:[...u,_,...x,...g,h,...v,y,...$];return`
            ${m.registerUniforms(l.map(A=>({name:`${cd(A)}`,type:"u32"}))).registerUniform("outputSize","u32").declareVariables(...i,d)}

            ${m.mainStart()}
            ${m.guardAgainstOutOfBoundsWorkgroupSizes("uniforms.outputSize")}
            var outputIndices = ${d.offsetToIndices("global_idx")};
            ${i.map((A,C)=>`var input${C}Indices: ${i[C].type.indices};`).join(`
`)}
            ${T.join(`
`)};
            ${d.setByOffset("global_idx","sum")};
          }`};return{name:"Einsum",shaderCache:{hint:r.equation,inputDependencies:e.map(()=>"rank")},getRunData:()=>{let m=l.filter(h=>r.symbolToInfo.has(h)).map(h=>({type:12,data:r.symbolToInfo.get(h)?.dimValue||0}));m.push({type:12,data:a});let u=e.map((h,_)=>[...N(h)]).reduce((h,_)=>h.concat(_),m);return u.push(...N(n)),{outputs:[{dims:n,dataType:t}],dispatchGroup:{x:Math.ceil(a/64)},programUniforms:u}},getShaderSource:p}},pd=(e,t)=>{let r=new $o(e.inputs,t.equation),n=r.outputDims,o=e.inputs.map((i,a)=>i.dims);e.compute(Af(o,e.inputs[0].dataType,r,n))},md=e=>{let t=e.equation.replace(/\s+/g,"");return ee({equation:t})}});var kf,hd,Ef,Pf,gd,bd=U(()=>{"use strict";J();ne();ae();kf=e=>{if(!e||e.length!==2)throw new Error("Expand requires 2 input.");let t=e[0].dims,r=Array.from(e[1].getBigInt64Array(),Number),n=r.length<t.length?0:r.length-t.length,o=t.length<r.length?0:t.length-r.length;for(;n<r.length&&o<t.length;++n,++o)if(r[n]!==t[o]&&r[n]!==1&&t[o]!==1)throw new Error("Expand requires shape to be broadcastable to input")},hd=(e,t)=>{let r=e.length-t.length,n=[];for(let o=0;o<r;++o)n.push(e[o]);for(let o=0;o<t.length;++o)n.push(t[o]===1?e[o+r]:t[o]);return n},Ef=(e,t)=>e.length>t.length?hd(e,t):hd(t,e),Pf=e=>{let t=e[0].dims,r=Array.from(e[1].getBigInt64Array(),Number),n=Ef(t,r),o=e[0].dataType,i=o===9||k.size(t)===1,a=o===9||t.length>0&&t[t.length-1]%4===0?4:1,d=i||n.length>0&&n[n.length-1]%4===0?4:1,l=Math.ceil(k.size(n)/d),p=u=>{let h=E("input",o,t.length,a),_=M("output",o,n.length,d),y;if(o===9){let g=(x,$,v="")=>`
          let outputIndices${$} = ${_.offsetToIndices(`outputOffset + ${$}u`)};
          let offset${$} = ${h.broadcastedIndicesToOffset(`outputIndices${$}`,_)};
          let index${$} = offset${$} / 4u;
          let component${$} = offset${$} % 4u;
          ${x}[${$}] = ${v}(${h.getByOffset(`index${$}`)}[component${$}]);
        `;y=`
        let outputOffset = global_idx * ${d};
        var data = vec4<u32>(0);
        ${g("data",0,"u32")}
        ${g("data",1,"u32")}
        ${g("data",2,"u32")}
        ${g("data",3,"u32")}
        ${_.setByOffset("global_idx","data")}
      }`}else y=`
        let outputIndices = ${_.offsetToIndices(`global_idx * ${d}`)};
        let inputOffset = ${h.broadcastedIndicesToOffset("outputIndices",_)};
        let data = ${_.type.value}(${h.getByOffset(`inputOffset / ${a}`)});
        ${_.setByOffset("global_idx","data")}
      }`;return`
    ${u.registerUniform("vec_size","u32").declareVariables(h,_)}
    ${u.mainStart()}
    ${u.guardAgainstOutOfBoundsWorkgroupSizes("uniforms.vec_size")}
    ${y}`},m=[{type:12,data:l},...N(t,n)];return{name:"Expand",shaderCache:{hint:`${n.length};${a}${d}`,inputDependencies:["rank"]},getShaderSource:p,getRunData:()=>({outputs:[{dims:n,dataType:e[0].dataType}],dispatchGroup:{x:Math.ceil(l/64)},programUniforms:m})}},gd=e=>{kf(e.inputs),e.compute(Pf(e.inputs),{inputs:[0]})}});var zf,yd,_d=U(()=>{"use strict";J();ne();ae();qr();zf=e=>{let t=e[0].dataType,r=k.size(e[0].dims),n=k.size(e[1].dims),o=n%4===0,i=a=>{let d=E("x",t,[1],4),l=E("bias",t,[1],4),p=M("y",t,[1],4),m=[{name:"output_vec_size",type:"u32"},{name:"bias_size",type:"u32"}],u=_=>`
      let bias${_}_offset: u32 = (global_idx * 4 + ${_}) % uniforms.bias_size;
      let bias${_} = ${l.getByOffset(`bias${_}_offset / 4`)}[bias${_}_offset % 4];`,h=o?`
      let bias = ${l.getByOffset("global_idx % (uniforms.bias_size / 4)")};`:`${u(0)}${u(1)}${u(2)}${u(3)}
      let bias = ${d.type.value}(bias0, bias1, bias2, bias3);`;return`${a.registerUniforms(m).declareVariables(d,l,p)}

    ${po(Ee(t))}

    ${a.mainStart(Et)}
      ${a.guardAgainstOutOfBoundsWorkgroupSizes("uniforms.output_vec_size")}

      let x = ${d.getByOffset("global_idx")};
      ${h}
      let x_in = x + bias;
      ${p.setByOffset("global_idx",mo("x_in"))}
    }`};return{name:"FastGeluWithBias",shaderCache:{hint:`${o}`,inputDependencies:["type","type"]},getShaderSource:i,getRunData:a=>({outputs:[{dims:a[0].dims,dataType:a[0].dataType}],programUniforms:[{type:12,data:Math.ceil(r/4)},{type:12,data:n}],dispatchGroup:{x:Math.ceil(r/Et/4)}})}},yd=e=>{e.inputs.length<2||k.size(e.inputs[1].dims)===0?fu(e):e.compute(zf(e.inputs))}});var Of,Df,wd,vd,$d=U(()=>{"use strict";J();ne();xe();ae();Of=e=>{if(!e||e.length!==2)throw new Error("Gather requires 2 inputs.")},Df=(e,t)=>{let r=e[0].dims,n=e[1].dims,o=r.length,i=k.normalizeAxis(t.axis,o),a=r.slice(0);a.splice(i,1,...n);let d=r[i],l=e[0].dataType===9?4:1,p=Math.ceil(k.size(a)/l),m=[{type:12,data:p},{type:6,data:d},{type:12,data:i},...N(e[0].dims,e[1].dims,a)],u=h=>{let _=E("data",e[0].dataType,e[0].dims.length,l),y=E("inputIndices",e[1].dataType,e[1].dims.length),g=M("output",e[0].dataType,a.length,l),x=v=>{let S=n.length,T=`var indicesIndices${v}  = ${y.type.indices}(0);`;for(let A=0;A<S;A++)T+=`${S>1?`indicesIndices${v}[${A}]`:`indicesIndices${v}`} = ${a.length>1?`outputIndices${v}[uniforms.axis + ${A}]`:`outputIndices${v}`};`;T+=`
          var idx${v} = ${y.getByIndices(`indicesIndices${v}`)};
          if (idx${v} < 0) {
            idx${v} = idx${v} + uniforms.axisDimLimit;
          }
          var dataIndices${v} : ${_.type.indices};
        `;for(let A=0,C=0;A<o;A++)A===i?(T+=`${o>1?`dataIndices${v}[${A}]`:`dataIndices${v}`} = u32(idx${v});`,C+=S):(T+=`${o>1?`dataIndices${v}[${A}]`:`dataIndices${v}`} = ${a.length>1?`outputIndices${v}[${C}]`:`outputIndices${v}`};`,C++);return T},$;if(e[0].dataType===9){let v=(S,T,A="")=>`
          let outputIndices${T} = ${g.offsetToIndices(`outputOffset + ${T}u`)};
          ${x(T)};
          let offset${T} = ${_.indicesToOffset(`dataIndices${T}`)};
          let index${T} = offset${T} / 4u;
          let component${T} = offset${T} % 4u;
          ${S}[${T}] = ${A}(${_.getByOffset(`index${T}`)}[component${T}]);
        `;$=`
        let outputOffset = global_idx * ${l};
        var value = vec4<u32>(0);
        ${v("value",0,"u32")}
        ${v("value",1,"u32")}
        ${v("value",2,"u32")}
        ${v("value",3,"u32")}
        ${g.setByOffset("global_idx","value")}
      `}else $=`
      let outputIndices = ${g.offsetToIndices("global_idx")};
      ${x("")};
      let value = ${_.getByIndices("dataIndices")};
      ${g.setByOffset("global_idx","value")};
      `;return`
      ${h.registerUniform("outputSize","u32").registerUniform("axisDimLimit","i32").registerUniform("axis","u32").declareVariables(_,y,g)}
      ${h.mainStart()}
        ${h.guardAgainstOutOfBoundsWorkgroupSizes("uniforms.outputSize")}
        ${$}
      }`};return{name:"Gather",shaderCache:{hint:t.cacheKey,inputDependencies:["rank","rank"]},getRunData:()=>({outputs:[{dims:a,dataType:e[0].dataType}],dispatchGroup:{x:Math.ceil(p/64)},programUniforms:m}),getShaderSource:u}},wd=e=>ee({axis:e.axis}),vd=(e,t)=>{let r=e.inputs;Of(r),e.compute(Df(e.inputs,t))}});var Bf,xd,Sd,Td=U(()=>{"use strict";J();ne();ae();Bf=(e,t,r,n,o,i,a,d,l)=>{let p=[{type:12,data:i},{type:12,data:n},{type:12,data:o},{type:12,data:r},{type:12,data:a},{type:12,data:d},{type:12,data:l}],m=[i];p.push(...N(t.dims,m));let u=h=>{let _=E("indices_data",t.dataType,t.dims.length),y=M("input_slice_offsets_data",12,1,1),g=[_,y],x=[{name:"output_size",type:"u32"},{name:"batch_dims",type:"u32"},{name:"input_dims",type:"u32",length:o.length},{name:"sizes_from_slice_dims_data",type:"u32",length:r.length},{name:"num_slices_per_batch",type:"u32"},{name:"input_batch_stride",type:"u32"},{name:"num_slice_dims",type:"u32"}];return`
  ${h.registerUniforms(x).declareVariables(...g)}
  ${h.mainStart()}
    ${h.guardAgainstOutOfBoundsWorkgroupSizes("uniforms.output_size")}
    let batch_idx = global_idx / uniforms.num_slices_per_batch;
    let base_offset = batch_idx * uniforms.input_batch_stride;

    let slice_indices_base_offset = global_idx * uniforms.num_slice_dims;
    var relative_slice_offset = 0;
    for (var dim_idx = 0u; dim_idx < uniforms.num_slice_dims; dim_idx ++) {
      var index = i32(indices_data[dim_idx + slice_indices_base_offset].x);
      let input_dim_idx = uniforms.batch_dims + dim_idx;
      if (index < 0) {
        ${o.length===1?"index += i32(uniforms.input_dims);":"index += i32(uniforms.input_dims[input_dim_idx]);"}
      }
      ${r.length===1?"relative_slice_offset += index * i32(uniforms.sizes_from_slice_dims_data);":"relative_slice_offset += index * i32(uniforms.sizes_from_slice_dims_data[dim_idx]);"}
    }

    input_slice_offsets_data[global_idx] =  base_offset + u32(relative_slice_offset);
  }`};return e.compute({name:"computeSliceOffsets",shaderCache:{hint:`${o.length}_${r.length}`,inputDependencies:["rank"]},getRunData:()=>({outputs:[{dims:m,dataType:e.inputs[1].dataType}],dispatchGroup:{x:Math.ceil(i/64)},programUniforms:p}),getShaderSource:u},{inputs:[t],outputs:[-1]})[0]},xd=(e,t)=>{let r=e.inputs,n=r[0].dims,o=r[0].dataType,i=r[1].dims,a=i[i.length-1],d=k.sizeToDimension(i,i.length-1),l=k.sizeFromDimension(n,t.batchDims+a),p=k.sizeToDimension(n,t.batchDims),m=k.sizeFromDimension(n,t.batchDims),u=d/p,h=new Array(a),_=l;for(let T=0;T<a;++T)h[a-1-T]=_,_*=n[t.batchDims+a-1-T];let y=Bf(e,r[1],h,t.batchDims,n,d,u,m,a),g=t.batchDims+a;if(g>n.length)throw new Error("last dimension of indices must not be larger than rank of input tensor");let x=i.slice(0,-1).concat(n.slice(g)),$=k.size(x),v=[{type:12,data:$},{type:12,data:l},...N(r[0].dims,y.dims,x)],S=T=>{let A=E("data",r[0].dataType,r[0].dims.length),C=E("slice_offsets",12,y.dims.length),P=M("output",r[0].dataType,x.length);return`
          ${T.registerUniform("output_size","u32").registerUniform("slice_size","u32").declareVariables(A,C,P)}
            ${T.mainStart()}
            ${T.guardAgainstOutOfBoundsWorkgroupSizes("uniforms.output_size")}
          let slice_offset = slice_offsets[global_idx / uniforms.slice_size];
          output[global_idx] = data[u32(slice_offset) + global_idx % uniforms.slice_size];
        }`};e.compute({name:"GatherND",shaderCache:{hint:t.cacheKey,inputDependencies:["rank","rank"]},getRunData:()=>({outputs:[{dims:x,dataType:o}],dispatchGroup:{x:Math.ceil($/64)},programUniforms:v}),getShaderSource:S},{inputs:[r[0],y]})},Sd=e=>({batchDims:e.batch_dims,cacheKey:""})});var Mf,Rf,Id,Cd,Ad=U(()=>{"use strict";J();ne();xe();ae();Mf=(e,t)=>{if(e.length<3||e.length>4)throw new Error("GatherBlockQuantized requires 3 or 4 inputs.");let r=k.normalizeAxis(t.quantizeAxis,e[0].dims.length),n=t.blockSize,o=e[0],i=e[2],a=e.length===4?e[3]:void 0;if(i.dims.length!==o.dims.length||!o.dims.map((d,l)=>l===r?Math.ceil(d/n)===i.dims[l]:d===i.dims[l]).reduce((d,l)=>d&&l,!0))throw new Error("Scales must have the same rank as the input tensor and the dims should match except on gatherAxis.");if(a){if(a.dataType!==o.dataType)throw new Error("Zero point must have the same data type as the input tensor.");if(a.dims.length!==i.dims.length||!a.dims.map((d,l)=>d===i.dims[l]).reduce((d,l)=>d&&l,!0))throw new Error("Zero point must have the same rank as the input tensor and the dims should match except on quantizeAxis.")}},Rf=(e,t)=>{let r=e[0].dims,n=e[1].dims,o=r.length,i=k.normalizeAxis(t.gatherAxis,o),a=k.normalizeAxis(t.quantizeAxis,o),d=r.slice(0);d.splice(i,1,...n);let l=k.size(d),p=e[2].dataType,u=e[0].dataType===22,h=[{type:12,data:l},{type:12,data:a},{type:12,data:i},{type:12,data:t.blockSize},...N(...e.map((y,g)=>y.dims),d)],_=y=>{let g=E("data",e[0].dataType,e[0].dims.length),x=E("inputIndices",e[1].dataType,e[1].dims.length),$=E("scales",e[2].dataType,e[2].dims.length),v=e.length>3?E("zeroPoint",e[3].dataType,e[3].dims.length):void 0,S=M("output",p,d.length),T=[g,x,$];v&&T.push(v);let A=[{name:"output_size",type:"u32"},{name:"quantize_axis",type:"u32"},{name:"gather_axis",type:"u32"},{name:"block_size",type:"u32"}];return`
        ${y.registerUniforms(A).declareVariables(...T,S)}
        ${y.mainStart()}
        let output_indices = ${S.offsetToIndices("global_idx")};
        var indices_indices = ${x.type.indices}(0);
        ${(()=>n.length>1?`
          for (var i: u32 = 0; i < ${n.length}; i++) {
            let index = ${S.indicesGet("output_indices","uniforms.gather_axis + i")};
            ${x.indicesSet("indices_indices","i","index")};
          }`:`indices_indices = ${S.indicesGet("output_indices","uniforms.gather_axis")};`)()};
        var data_indices = ${g.type.indices}(0);
        for (var i: u32 = 0; i < uniforms.gather_axis; i++) {
          let index = ${S.indicesGet("output_indices","i")};
          ${g.indicesSet("data_indices","i","index")};
        }
        var index_from_indices = ${x.getByIndices("indices_indices")};
        if (index_from_indices < 0) {
          index_from_indices += ${r[i]};
        }
        ${g.indicesSet("data_indices","uniforms.gather_axis","u32(index_from_indices)")};
        for (var i = uniforms.gather_axis + 1; i < ${d.length}; i++) {
          let index = ${S.indicesGet("output_indices",`i + ${n.length} - 1`)};
          ${g.indicesSet("data_indices","i","index")};
        }
        let data_offset = ${g.indicesToOffset("data_indices")};
        let data_index = data_offset % 8;
        // Convert 4-bit packed data to 8-bit packed data.
        let packed_4bit_quantized_data = ${g.getByOffset("data_offset / 8")};
        let packed_8bit_quantized_data = (packed_4bit_quantized_data >> (4 * (data_index % 2))) & 0x0f0f0f0f;
        let quantized_data_vec = ${u?"unpack4xI8":"unpack4xU8"}(u32(packed_8bit_quantized_data));
        let quantized_data = quantized_data_vec[data_index / 2];
        var scale_indices = data_indices;
        let quantize_axis_index = ${$.indicesGet("data_indices","uniforms.quantize_axis")} / uniforms.block_size;
        ${$.indicesSet("scale_indices","uniforms.quantize_axis","quantize_axis_index")};
        var scale = ${$.getByIndices("scale_indices")};
        ${(()=>v?`
              let zero_point_indices = scale_indices;
              let zero_point_offset = ${v.indicesToOffset("zero_point_indices")};
              let zero_point_index = zero_point_offset % 8;
              let packed_4bit_zero_points = ${v.getByOffset("zero_point_offset / 8")};
              let packed_8bit_zero_points = (packed_4bit_zero_points >> (4 * (zero_point_index % 2))) & 0x0f0f0f0f;
              let zero_point_vec = ${u?"unpack4xI8":"unpack4xU8"}(u32(packed_8bit_zero_points));
              let zero_point = zero_point_vec[zero_point_index / 2];`:"var zero_point = 0")()};
        let dequantized_data = ${Ee(p)}(quantized_data - zero_point) * scale;
        ${S.setByOffset("global_idx","dequantized_data")};
    }`};return{name:"GatherBlockQuantized",shaderCache:{hint:`${t.cacheKey};${e.filter((y,g)=>g!==1).map(y=>y.dims.join("_")).join(";")}`,inputDependencies:Array.from({length:e.length},(y,g)=>"rank")},getRunData:()=>({outputs:[{dims:d,dataType:p}],dispatchGroup:{x:Math.ceil(l/64)},programUniforms:h}),getShaderSource:_}},Id=(e,t)=>{let r=e.inputs;Mf(r,t),e.compute(Rf(e.inputs,t))},Cd=e=>ee({blockSize:e.blockSize,gatherAxis:e.gatherAxis,quantizeAxis:e.quantizeAxis})});var Uf,Nf,kd,Ed,Pd=U(()=>{"use strict";J();ne();xe();ae();Uf=e=>{if(!e||e.length!==2)throw new Error("GatherElements requires 2 inputs.");if(e[0].dims.length<1)throw new Error("GatherElements requires that the data input be rank >= 1.");if(e[0].dims.length!==e[1].dims.length)throw new Error(`GatherElements requires that the data input and
                     indices input tensors be of same rank.`)},Nf=(e,t)=>{let r=e[0].dims,n=e[0].dataType,o=r.length,i=e[1].dims,a=e[1].dataType,d=k.normalizeAxis(t.axis,o),l=r[d],p=i.slice(0),m=k.size(p),u=E("input",n,o),h=E("indicesInput",a,i.length),_=M("output",n,p.length),y=[{type:12,data:m},{type:6,data:l},{type:12,data:d}];return y.push(...N(r,i,p)),{name:"GatherElements",shaderCache:{inputDependencies:["rank","rank"]},getRunData:()=>({outputs:[{dims:p,dataType:e[0].dataType}],dispatchGroup:{x:Math.ceil(m/64)},programUniforms:y}),getShaderSource:$=>`
      ${$.registerUniform("outputSize","u32").registerUniform("axisDimLimit","i32").registerUniform("axis","u32").declareVariables(u,h,_)}
      ${$.mainStart()}
      ${$.guardAgainstOutOfBoundsWorkgroupSizes("uniforms.outputSize")}

      let outputIndices = ${_.offsetToIndices("global_idx")};

      var idx = ${h.getByOffset("global_idx")};
      if (idx < 0) {
        idx = idx + uniforms.axisDimLimit;
      }
      var inputIndices = ${u.type.indices}(outputIndices);
      ${u.indicesSet("inputIndices","uniforms.axis","u32(idx)")};
      let value = ${u.getByIndices("inputIndices")};

      ${_.setByOffset("global_idx","value")};
  }`}},kd=e=>ee({axis:e.axis}),Ed=(e,t)=>{let r=e.inputs;Uf(r),e.compute(Nf(e.inputs,t))}});var Vf,Wf,zd,Od,Dd=U(()=>{"use strict";J();ne();ae();Vf=e=>{if(!e)throw new Error("Input is missing");if(e.length<2||e.length>3)throw new Error("Invaid input number.");if(e.length===3&&e[2].dims.length>2)throw new Error("Invalid input shape of C");if(e[0].dataType!==e[1].dataType||e.length===3&&e[0].dataType!==e[2].dataType)throw new Error("Input types are mismatched")},Wf=(e,t)=>{let r=e[0].dims.slice(),n=e[1].dims.slice(),[o,i,a]=Nr.getShapeOfGemmResult(r,t.transA,n,t.transB,e.length===3?e[2].dims:void 0),d=[o,i];if(!d)throw new Error("Can't use gemm on the given tensors");let l=16,p=Math.ceil(i/l),m=Math.ceil(o/l),u=!0,h=k.size(d),_=[{type:12,data:u?p:h},{type:12,data:o},{type:12,data:i},{type:12,data:a},{type:1,data:t.alpha},{type:1,data:t.beta}],y=["type","type"];e.length===3&&(_.push(...N(e[2].dims)),y.push("rank")),_.push(...N(d));let g=$=>{let v="";t.transA&&t.transB?v="value += a[k * uniforms.M + m] * b[n * uniforms.K + k];":t.transA&&!t.transB?v="value += a[k * uniforms.M + m] * b[k * uniforms.N + n];":!t.transA&&t.transB?v="value += a[m * uniforms.K + k] * b[n * uniforms.K + k];":!t.transA&&!t.transB&&(v="value += a[m * uniforms.K + k] * b[k * uniforms.N + n];");let S=t.alpha===1?"":"value *= uniforms.alpha;",T=E("a",e[0].dataType,e[0].dims),A=E("b",e[1].dataType,e[1].dims),C=T.type.value,P=null,D=[T,A];e.length===3&&(P=E("c",e[2].dataType,e[2].dims.length),D.push(P));let R=M("output",e[0].dataType,d.length);D.push(R);let H=[{name:"output_size",type:"u32"},{name:"M",type:"u32"},{name:"N",type:"u32"},{name:"K",type:"u32"},{name:"alpha",type:"f32"},{name:"beta",type:"f32"}];return`
  ${$.registerUniforms(H).declareVariables(...D)}

  ${$.mainStart()}
    ${$.guardAgainstOutOfBoundsWorkgroupSizes("uniforms.output_size")}

    let m = global_idx / uniforms.N;
    let n = global_idx % uniforms.N;

    var value = ${C}(0);
    for (var k: u32 = 0u; k < uniforms.K; k++) {
      ${v}
    }

    ${S}
    ${(()=>P!=null?`let cOffset = ${P.broadcastedIndicesToOffset("vec2(m, n)",R)}; value += ${C}(uniforms.beta) * ${P.getByOffset("cOffset")};`:"")()}
    output[global_idx] = value;
  }`},x=$=>{let v=E("a",e[0].dataType,e[0].dims),S=E("b",e[1].dataType,e[1].dims),T=null,A=[v,S];e.length===3&&(T=E("c",e[2].dataType,e[2].dims.length),A.push(T));let C=M("output",e[0].dataType,d.length);A.push(C);let P=[{name:"num_tile_n",type:"u32"},{name:"M",type:"u32"},{name:"N",type:"u32"},{name:"K",type:"u32"},{name:"alpha",type:"f32"},{name:"beta",type:"f32"}],D="",R="";t.transA&&t.transB?(R=`
      var col = tile_row_start + local_id.x;
      var row = k_start + local_id.y;
      if (col < uniforms.M && row < uniforms.K) {
        tile_a[local_id.y][local_id.x] = a[row * uniforms.M + col];
      } else {
        tile_a[local_id.y][local_id.x] = ${v.type.value}(0);
      }

      col = k_start + local_id.x;
      row = tile_col_start + local_id.y;
      if (col < uniforms.K && row < uniforms.N) {
        tile_b[local_id.y][local_id.x] = b[row * uniforms.K + col];
      } else {
        tile_b[local_id.y][local_id.x] = ${S.type.value}(0);
      }
      `,D="value += tile_a[k][local_id.y] * tile_b[local_id.x][k];"):t.transA&&!t.transB?(R=`
      var col = tile_row_start + local_id.x;
      var row = k_start + local_id.y;
      if (col < uniforms.M && row < uniforms.K) {
        tile_a[local_id.y][local_id.x] = a[row * uniforms.M + col];
      } else {
        tile_a[local_id.y][local_id.x] = ${v.type.value}(0);
      }

      col = tile_col_start + local_id.x;
      row = k_start + local_id.y;
      if (col < uniforms.N && row < uniforms.K) {
        tile_b[local_id.y][local_id.x] = b[row * uniforms.N + col];
      } else {
        tile_b[local_id.y][local_id.x] = ${S.type.value}(0);
      }
      `,D="value += tile_a[k][local_id.y] * tile_b[k][local_id.x];"):!t.transA&&t.transB?(R=`
      var col = k_start + local_id.x;
      var row = tile_row_start + local_id.y;
      if (col < uniforms.K && row < uniforms.M) {
        tile_a[local_id.y][local_id.x] = a[row * uniforms.K + col];
      } else {
        tile_a[local_id.y][local_id.x] = ${v.type.value}(0);
      }

      col = k_start + local_id.x;
      row = tile_col_start + local_id.y;
      if (col < uniforms.K && row < uniforms.N) {
        tile_b[local_id.y][local_id.x] = b[row * uniforms.K + col];
      } else {
        tile_b[local_id.y][local_id.x] = ${S.type.value}(0);
      }
      `,D="value += tile_a[local_id.y][k] * tile_b[local_id.x][k];"):!t.transA&&!t.transB&&(R=`
      var col = k_start + local_id.x;
      var row = tile_row_start + local_id.y;
      if (col < uniforms.K && row < uniforms.M) {
        tile_a[local_id.y][local_id.x] = a[row * uniforms.K + col];
      } else {
        tile_a[local_id.y][local_id.x] = ${v.type.value}(0);
      }

      col = tile_col_start + local_id.x;
      row = k_start + local_id.y;
      if (col < uniforms.N && row < uniforms.K) {
        tile_b[local_id.y][local_id.x] = b[row * uniforms.N + col];
      } else {
        tile_b[local_id.y][local_id.x] = ${S.type.value}(0);
      }
      `,D="value += tile_a[local_id.y][k] * tile_b[k][local_id.x];");let H=t.alpha===1?"":"value *= uniforms.alpha;";return`
  ${$.registerUniforms(P).declareVariables(...A)}
  var<workgroup> tile_a: array<array<${v.type.storage}, ${l}>, ${l}>;
  var<workgroup> tile_b: array<array<${S.type.storage}, ${l}>, ${l}>;
  ${$.mainStart([l,l,1])}
    let tile_col_start = (workgroup_index % uniforms.num_tile_n) * ${l};
    let tile_row_start = (workgroup_index / uniforms.num_tile_n) * ${l};
    let num_tiles = (uniforms.K - 1) / ${l} + 1;
    var k_start = 0u;
    var value = ${C.type.value}(0);
    for (var t: u32 = 0u; t < num_tiles; t++) {
      ${R}
      k_start = k_start + ${l};
      workgroupBarrier();

      for (var k: u32 = 0u; k < ${l}; k++) {
        ${D}
      }
      workgroupBarrier();
    }

    ${H}
    let m = tile_row_start + local_id.y;
    let n = tile_col_start + local_id.x;
    ${(()=>T!=null?`let cOffset = ${T.broadcastedIndicesToOffset("vec2(m, n)",C)}; value += ${C.type.value}(uniforms.beta) * ${T.getByOffset("cOffset")};`:"")()}
    if (m < uniforms.M && n < uniforms.N) {
      output[m * uniforms.N + n] = value;
    }
  }`};return u?{name:"GemmShared",shaderCache:{hint:`${t.cacheKey}`,inputDependencies:y},getRunData:()=>({outputs:[{dims:d,dataType:e[0].dataType}],dispatchGroup:{x:p*m},programUniforms:_}),getShaderSource:x}:{name:"Gemm",shaderCache:{hint:`${t.cacheKey}`,inputDependencies:y},getRunData:()=>({outputs:[{dims:d,dataType:e[0].dataType}],dispatchGroup:{x:Math.ceil(h/64)},programUniforms:_}),getShaderSource:g}},zd=e=>{let t=e.transA,r=e.transB,n=e.alpha,o=e.beta;return{transA:t,transB:r,alpha:n,beta:o,cacheKey:`${e.transA};${e.transB};${e.alpha===1}`}},Od=(e,t)=>{Vf(e.inputs),e.compute(Wf(e.inputs,t))}});var lt,_t,Nt,Vt,Lf,Gf,Hf,Ff,qf,Kf,jf,Yf,Bd,Md,Rd=U(()=>{"use strict";J();ne();xe();ae();[lt,_t,Nt,Vt]=[0,1,2,3],Lf=e=>{if(e[0].dims.length!==4)throw new Error("only 4-D tensor is supported.");if(e[0].dims.length!==e[1].dims.length)throw new Error("input dimensions must be equal to grid dimensions");if(e[0].dims.length-2!==e[1].dims[e[1].dims.length-1])throw new Error(`last dimension of grid must be equal to ${e[0].dims.length-2}`);if(e[0].dims[0]!==e[1].dims[0])throw new Error("grid batch size must match input batch size")},Gf=`
  fn gs_get_cubic_coeffs(x: f32) -> vec4<f32> {
    let cubic_alpha = -0.75f;
    let x_abs = abs(x);
    var coeffs: vec4<f32>;
    coeffs[0] = (((cubic_alpha * (x_abs + 1) - 5 * cubic_alpha) * (x_abs + 1) + 8 * cubic_alpha) * (x_abs + 1) - 4 * cubic_alpha);
    coeffs[1] = (((cubic_alpha + 2) * x_abs - (cubic_alpha + 3)) * x_abs * x_abs + 1);
    coeffs[2] = (((cubic_alpha + 2) * (1 - x_abs) - (cubic_alpha + 3)) * (1 - x_abs) * (1 - x_abs) + 1);
    coeffs[3] = (((cubic_alpha * (2 - x_abs) - 5 * cubic_alpha) * (2 - x_abs) + 8 * cubic_alpha) * (2 - x_abs) - 4 * cubic_alpha);
    return coeffs;
  }
`,Hf=e=>`
  fn gs_bicubic_interpolate(p: mat4x4<${e}>, x: f32, y: f32) -> ${e} {
    var v: vec4<f32>;
    var coeffs = gs_get_cubic_coeffs(x);
    for (var i = 0; i < 4; i++) {
      v[i] = coeffs[0] * p[i][0] + coeffs[1] * p[i][1] + coeffs[2] * p[i][2] + coeffs[3] * p[i][3];
    }
    coeffs = gs_get_cubic_coeffs(y);
    let pixel = ${e}(coeffs[0] * v[0] + coeffs[1] * v[1] + coeffs[2] * v[2] + coeffs[3] * v[3]);
    return pixel;
  }
`,Ff=e=>`
  fn gs_denormalize(n: f32, length: i32) -> f32 {
    ${e.alignCorners===0?`
    // alignCorners: false => [-1, 1] to [-0.5, length - 0.5]
    return ((n + 1.0) * f32(length) - 1.0) / 2.0;
    `:`
    // alignCorners: true => [-1, 1] to [0, length - 1]
    return (n + 1.0) / 2.0 * (f32(length - 1));
    `}
  }
`,qf=e=>`
  ${e.paddingMode==="reflection"?`
      fn gs_reflect(x: i32, x_min: f32, x_max: f32) -> u32 {
        var dx = 0.0;
        var fx = f32(x);
        let range = x_max - x_min;
        if (fx < x_min) {
          dx = x_min - fx;
          let n = u32(dx / range);
          let r = dx - f32(n) * range;
          if (n % 2 == 0) {
            fx = x_min + r;
          } else {
            fx = x_max - r;
          }
        } else if (fx > x_max) {
          dx = fx - x_max;
          let n = u32(dx / range);
          let r = dx - f32(n) * range;
          if (n % 2 == 0) {
            fx = x_max - r;
          } else {
            fx = x_min + r;
          }
        }
        return u32(fx);
      }`:""}
`,Kf=(e,t,r)=>`
  fn pixel_at_grid(r: i32, c: i32, H: i32, W: i32, batch: u32, channel: u32, border: vec4<f32>) -> ${t} {
     var pixel = ${t}(0);
     var indices = vec4<u32>(0);
     indices[${lt}] = batch;
     indices[${_t}] = channel;`+(()=>{switch(r.paddingMode){case"zeros":return`
          if (r >= 0 && r < H && c >=0 && c < W) {
            indices[${Nt}] = u32(r);
            indices[${Vt}] = u32(c);
          }
        `;case"border":return`
          indices[${Nt}] = u32(clamp(r, 0, H - 1));
          indices[${Vt}] = u32(clamp(c, 0, W - 1));
        `;case"reflection":return`
          indices[${Nt}] = gs_reflect(r, border[1], border[3]);
          indices[${Vt}] = gs_reflect(c, border[0], border[2]);
        `;default:throw new Error(`padding mode ${r.paddingMode} is not supported`)}})()+`
    return ${e.getByIndices("indices")};
  }
`,jf=(e,t,r)=>(()=>{switch(r.mode){case"nearest":return`
          let result = pixel_at_grid(i32(round(y)), i32(round(x)), H_in, W_in, indices[${lt}], indices[${_t}], border);
        `;case"bilinear":return`
          let x1 = i32(floor(x));
          let y1 = i32(floor(y));
          let x2 = x1 + 1;
          let y2 = y1 + 1;

          let p11 = pixel_at_grid(y1, x1, H_in, W_in, indices[${lt}], indices[${_t}], border);
          let p12 = pixel_at_grid(y1, x2, H_in, W_in, indices[${lt}], indices[${_t}], border);
          let p21 = pixel_at_grid(y2, x1, H_in, W_in, indices[${lt}], indices[${_t}], border);
          let p22 = pixel_at_grid(y2, x2, H_in, W_in, indices[${lt}], indices[${_t}], border);

          let dx2 = ${t}(f32(x2) - x);
          let dx1 = ${t}(x - f32(x1));
          let dy2 = ${t}(f32(y2) - y);
          let dy1 = ${t}(y - f32(y1));
          let result = dy2 * (dx2 * p11 + dx1 * p12) + dy1 * (dx2 * p21 + dx1 * p22);
        `;case"bicubic":return`
          let x0 = i32(floor(x)) - 1;
          let y0 = i32(floor(y)) - 1;
          var p: mat4x4<${t}>;
          for (var h = 0; h < 4; h++) {
            for (var w = 0; w < 4; w++) {
              p[h][w] = pixel_at_grid(h + y0, w + x0, H_in, W_in, indices[${lt}], indices[${_t}], border);
            }
          }

          let dx = x - f32(x0 + 1);
          let dy = y - f32(y0 + 1);
          let result = gs_bicubic_interpolate(p, dx, dy);
        `;default:throw new Error(`mode ${r.mode} is not supported`)}})()+`${e.setByOffset("global_idx","result")}`,Yf=(e,t)=>{let r=E("x",e[0].dataType,e[0].dims.length),n=[e[1].dims[0],e[1].dims[1],e[1].dims[2]],o=E("grid",e[1].dataType,n.length,2),i=[e[0].dims[0],e[0].dims[1],e[1].dims[1],e[1].dims[2]];t.format==="NHWC"&&(i=[e[0].dims[0],e[1].dims[1],e[1].dims[2],e[0].dims[3]],[lt,_t,Nt,Vt]=[0,3,1,2]);let a=M("output",e[0].dataType,i.length),d=r.type.value,l=k.size(i),p=[{type:12,data:l},...N(e[0].dims,n,i)],m=u=>`
  ${u.registerUniform("output_size","u32").declareVariables(r,o,a)}
  ${Gf}
  ${Hf(d)}
  ${Ff(t)}
  ${qf(t)}
  ${Kf(r,d,t)}

  ${u.mainStart()}
    ${u.guardAgainstOutOfBoundsWorkgroupSizes("uniforms.output_size")}
      let H_in = i32(uniforms.x_shape[${Nt}]);
      let W_in = i32(uniforms.x_shape[${Vt}]);

      ${t.alignCorners===0?`
      let x_min = -0.5;
      let x_max = f32(W_in) - 0.5;
      let y_min = -0.5;
      let y_max = f32(H_in) - 0.5;
      `:`
      let x_min = 0.0;
      let x_max = f32(W_in) - 1.0;
      let y_min = 0.0;
      let y_max = f32(H_in) - 1.0;
      `};
      let border = vec4<f32>(x_min, y_min, x_max, y_max);

      let indices = ${a.offsetToIndices("global_idx")};
      var grid_indices = vec3<u32>(indices[${lt}], indices[${Nt}], indices[${Vt}]);
      let nxy = ${o.getByIndices("grid_indices")};
      var x = gs_denormalize(f32(nxy[0]), W_in);
      var y = gs_denormalize(f32(nxy[1]), H_in);

      ${jf(a,d,t)}
  }`;return{name:"GridSample",shaderCache:{hint:`${t.cacheKey}`,inputDependencies:["type","type"]},getRunData:u=>{let h=k.size(i);return{outputs:[{dims:i,dataType:u[0].dataType}],dispatchGroup:{x:Math.ceil(h/64)},programUniforms:p}},getShaderSource:m}},Bd=(e,t)=>{Lf(e.inputs),e.compute(Yf(e.inputs,t))},Md=e=>ee({alignCorners:e.align_corners,mode:e.mode,paddingMode:e.padding_mode,format:e.format})});var Me,Xf,Nd,Ud,Jf,er,Vd,xo=U(()=>{"use strict";J();ne();xe();Ur();Hr();ae();dt();Me=(e,t)=>e.length>t&&e[t].dims.length>0?e[t]:void 0,Xf=(e,t)=>{let r=e[0],n=Me(e,1),o=Me(e,2),i=Me(e,3),a=Me(e,4),d=Me(e,5),l=Me(e,6),p=Me(e,7);if(r.dims.length!==3&&r.dims.length!==5)throw new Error("Input query is expected to have 3 or 5 dimensions");let m=r.dims[0],u=r.dims[1],h=r.dims.length===3?r.dims[2]:t.numHeads*r.dims[4],_=u,y=0,g=0,x=Math.floor(h/t.numHeads);if(l&&p&&k.size(l.dims)&&k.size(p.dims)){if(l.dims.length!==4)throw new Error('Input "past_key" is expected to have 4 dimensions');if(l.dims[0]!==m||l.dims[1]!==t.numHeads||l.dims[3]!==x)throw new Error('Input "past_key" shape (batch_size, num_heads, past_sequence_length, head_size)');if(p.dims[0]!==m||p.dims[1]!==t.numHeads||p.dims[3]!==x)throw new Error('Input "past_value" shape (batch_size, num_heads, past_sequence_length, head_size)');if(l.dims[2]!==p.dims[2])throw new Error('Input "past_key" and "past_value" shall have same dim 2 (past_sequence_length)');if(p.dims.length!==4)throw new Error('Input "past_value" is expected to have 4 dimensions');y=l.dims[2],g=l.dims[2]}else if(l&&k.size(l.dims)||p&&k.size(p.dims))throw new Error('Input "past_key" and "past_value" shall be both present or both absent');let $;if(n&&k.size(n.dims)>0){if(r.dims.length!==3)throw new Error('Input "query" is expected to have 3 dimensions when key is given');if(n.dims.length<3||n.dims.length>5)throw new Error('Input "key" is expected to have 3, 4, or 5 dimensions');if(r.dims[0]!==n.dims[0])throw new Error('Input "query" and "key" shall have same dim 0 (batch size)');if(n.dims.length===3){if(n.dims[2]!==r.dims[2])throw new Error('Input "query" and "key" shall have same dim 2 (hidden_size)');$=2,_=n.dims[1]}else if(n.dims.length===5){if(n.dims[2]!==t.numHeads||n.dims[3]!==2||n.dims[4]!==x)throw new Error('Expect "key" shape (batch_size, kv_sequence_length, num_heads, 2, head_size) for packed kv');if(o)throw new Error('Expect "value" be none when "key" has packed kv format.');$=5,_=n.dims[1]}else{if(n.dims[1]!==t.numHeads||n.dims[3]!==x)throw new Error('Expect "key" shape (batch_size, num_heads, kv_sequence_length, head_size) for past_key');$=0,_=n.dims[2]}}else{if(r.dims.length!==5)throw new Error('Input "query" is expected to have 5 dimensions when key is empty');if(r.dims[2]!==t.numHeads||r.dims[3]!==3)throw new Error('Expect "query" shape (batch_size, kv_sequence_length, num_heads, 3, head_size) for packed kv');$=3}if(i&&k.size(i.dims)>0){if(i.dims.length!==1)throw new Error('Input "bias" is expected to have 1 dimension');if(n&&n.dims.length===5&&n.dims[3]===2)throw new Error("bias is not allowed for packed kv.")}let v=y+_,S=0;if(a&&k.size(a.dims)>0){S=8;let P=a.dims;throw P.length===1?P[0]===m?S=1:P[0]===3*m+2&&(S=3):P.length===2&&P[0]===m&&P[1]===v&&(S=5),S===8?new Error('Input "key_padding_mask" shape shall be (batch_size) or (batch_size, total_sequence_length)'):new Error("Mask not supported")}let T=!1,A=h;if(o&&k.size(o.dims)>0){if(o.dims.length!==3&&o.dims.length!==4)throw new Error('Input "value" is expected to have 3 or 4 dimensions');if(r.dims[0]!==o.dims[0])throw new Error('Input "query" and "value" shall have same dim 0 (batch_size)');if(o.dims.length===3){if(_!==o.dims[1])throw new Error('Input "key" and "value" shall have the same dim 1 (kv_sequence_length)');A=o.dims[2]}else{if(_!==o.dims[2])throw new Error('Input "key" and "value" shall have the same dim 2 (kv_sequence_length)');A=o.dims[1]*o.dims[3],T=!0}}let C=!1;if(a&&k.size(a.dims)>0)throw new Error("Key padding mask is not supported");if(d&&k.size(d.dims)>0){if(d.dims.length!==4)throw new Error('Input "attention_bias" is expected to have 4 dimensions');if(d.dims[0]!==m||d.dims[1]!==t.numHeads||d.dims[2]!==u||d.dims[3]!==v)throw new Error('Expect "attention_bias" shape (batch_size, num_heads, sequence_length, total_sequence_length)')}return{batchSize:m,sequenceLength:u,pastSequenceLength:y,kvSequenceLength:_,totalSequenceLength:v,maxSequenceLength:g,inputHiddenSize:0,hiddenSize:h,vHiddenSize:A,headSize:x,vHeadSize:Math.floor(A/t.numHeads),numHeads:t.numHeads,isUnidirectional:!1,pastPresentShareBuffer:!1,maskFilterValue:t.maskFilterValue,maskType:S,scale:t.scale,broadcastResPosBias:C,passPastInKv:T,qkvFormat:$}},Nd=e=>ee({...e}),Ud=ee({perm:[0,2,1,3]}),Jf=(e,t,r,n,o,i,a)=>{let d=[n,o,i],l=k.size(d),p=[{type:12,data:l},{type:12,data:a},{type:12,data:i}],m=u=>{let h=M("qkv_with_bias",t.dataType,d),_=E("qkv",t.dataType,d),y=E("bias",r.dataType,d),g=[{name:"output_size",type:"u32"},{name:"bias_offset",type:"u32"},{name:"hidden_size",type:"u32"}];return`
  ${u.registerUniforms(g).declareVariables(_,y,h)}
  ${u.mainStart()}
    ${u.guardAgainstOutOfBoundsWorkgroupSizes("uniforms.output_size")}
    let bias_offset_idx = (global_idx % uniforms.hidden_size) + uniforms.bias_offset;

    qkv_with_bias[global_idx] = qkv[global_idx] + bias[bias_offset_idx];
  }`};return e.compute({name:"MultiHeadAttentionAddBias",shaderCache:{inputDependencies:["type","type"]},getRunData:()=>({outputs:[{dims:d,dataType:t.dataType,gpuDataType:0}],dispatchGroup:{x:Math.ceil(l/64)},programUniforms:p}),getShaderSource:m},{inputs:[t,r],outputs:[-1]})[0]},er=(e,t,r,n,o,i,a,d)=>{let l=i;if(a&&k.size(a.dims)>0){if(n===1)throw new Error("AddBiasReshape is not implemented. Please export your model with packed QKV or KV");return l=Jf(e,i,a,t,n,r*o,d),l=l.reshape([t,n,r,o]),r===1||n===1?l:e.compute(Pe(l,Ud.perm),{inputs:[l],outputs:[-1]})[0]}else return i.dims.length===3&&(l=i.reshape([t,n,r,o])),r===1||n===1?l:e.compute(Pe(l,Ud.perm),{inputs:[l],outputs:[-1]})[0]},Vd=(e,t)=>{let r=Xf(e.inputs,t),n=e.inputs[0],o=Me(e.inputs,1),i=Me(e.inputs,2),a=Me(e.inputs,3),d=Me(e.inputs,4),l=Me(e.inputs,5),p=Me(e.inputs,6),m=Me(e.inputs,7);if(n.dims.length===5)throw new Error("Packed QKV is not implemented");if(o?.dims.length===5)throw new Error("Packed KV is not implemented");let u=o&&i&&o.dims.length===4&&i.dims.length===4,h=er(e,r.batchSize,r.numHeads,r.sequenceLength,r.headSize,n,a,0);if(u)return Ut(e,h,o,i,d,void 0,p,m,l,r);if(!o||!i)throw new Error("key and value must be provided");let _=er(e,r.batchSize,r.numHeads,r.kvSequenceLength,r.headSize,o,a,r.hiddenSize),y=er(e,r.batchSize,r.numHeads,r.kvSequenceLength,r.vHeadSize,i,a,2*r.hiddenSize);Ut(e,h,_,y,d,void 0,p,m,l,r)}});var eh,th,rh,nh,So,Wd,Ld,To=U(()=>{"use strict";J();ne();xe();ae();eh=e=>{if(!e||e.length<1)throw new Error("too few inputs")},th=(e,t)=>{let r=[],n=t.numOutputs;return e[1].dims[0]>0&&(e[1].getBigInt64Array().forEach(o=>r.push(Number(o))),n=r.length),ee({numOutputs:n,axis:t.axis,splitSizes:r})},rh=e=>`
fn calculateOutputIndex(index: u32) -> u32 {
    for (var i: u32 = 0u; i < ${e}u; i += 1u ) {
    if (index < ${q("uniforms.size_in_split_axis","i",e)}) {
        return i;
    }
    }
    return ${e}u;
}`,nh=e=>{let t=e.length,r=[];for(let n=0;n<t;++n){let o=e[n].setByIndices("indices","input[global_idx]");t===1?r.push(o):n===0?r.push(`if (output_number == ${n}u) { ${o} }`):n===t-1?r.push(`else { ${o} }`):r.push(`else if (output_number == ${n}) { ${o} }`)}return`
      fn writeBufferData(output_number: u32, indices: ${e[0].type.indices}, global_idx: u32) {
        ${r.join(`
`)}
      }`},So=(e,t)=>{let r=e[0].dims,n=k.size(r),o=e[0].dataType,i=k.normalizeAxis(t.axis,r.length),a=new Array(t.numOutputs),d=E("input",o,r.length),l=new Array(t.numOutputs),p=[],m=[],u=0,h=[{type:12,data:n}];for(let y=0;y<t.numOutputs;y++){u+=t.splitSizes[y],l[y]=u;let g=r.slice();g[i]=t.splitSizes[y],m.push(g),a[y]=M(`output${y}`,o,g.length),p.push({dims:m[y],dataType:e[0].dataType})}h.push({type:12,data:l},...N(r,...m));let _=y=>`
  ${y.registerUniform("input_size","u32").registerUniform("size_in_split_axis","u32",l.length).declareVariables(d,...a)}
  ${rh(l.length)}
  ${nh(a)}

  ${y.mainStart()}
    ${y.guardAgainstOutOfBoundsWorkgroupSizes("uniforms.input_size")}

    var indices = ${d.offsetToIndices("global_idx")};
    var index = ${d.indicesGet("indices",i)};
    let output_number = calculateOutputIndex(index);
    if (output_number != 0) {
      index -= ${q("uniforms.size_in_split_axis","output_number - 1u",l.length)};
      ${d.indicesSet("indices",i,"index")};
    }
    writeBufferData(output_number, indices, global_idx);
  }`;return{name:"Split",shaderCache:{hint:t.cacheKey,inputDependencies:["rank"]},getShaderSource:_,getRunData:()=>({outputs:p,dispatchGroup:{x:Math.ceil(n/64)},programUniforms:h})}},Wd=(e,t)=>{eh(e.inputs);let r=e.inputs.length===1?t:th(e.inputs,t);e.compute(So(e.inputs,r),{inputs:[0]})},Ld=e=>{let t=e.axis,r=e.splitSizes,n=e.numOutputs<0?r.length:e.numOutputs;if(n!==r.length)throw new Error("numOutputs and splitSizes lengh must be equal");return ee({axis:t,numOutputs:n,splitSizes:r})}});var oh,ih,Gd,Hd,Fd=U(()=>{"use strict";xe();Hr();xo();To();dt();oh=(e,t)=>{if(t.doRotary)throw new Error("GroupQuerryAttention do_rotary attribute is not supported");if(t.doRotary&&e.length<=7)throw new Error("cos_cache and sin_cache inputs are required if do_rotary is specified");let r=e[0],n=e[1],o=e[2],i=e[3],a=e[4];if(t.localWindowSize!==-1)throw new Error("Local attention is not supported");if(t.softcap!==0)throw new Error("Softcap is not supported");if(t.rotaryInterleaved!==0)throw new Error("Rotary interleaved is not supported");if(t.smoothSoftmax)throw new Error("Smooth softmax is not supported");if(r.dims.length!==3&&r.dims.length!==5)throw new Error("Input query is expected to have 3 or 5 dimensions");let d=!1,l=r.dims[0],p=r.dims[1],m=r.dims.length===3?d?r.dims[2]/3:r.dims[2]:t.numHeads*r.dims[4],u=p,h=0,_=!n||n.dims.length===0,y=Math.floor(_?m/(t.numHeads+2*t.kvNumHeads):m/t.numHeads);_&&(m=y*t.numHeads);let g=i&&i.dims.length!==0,x=a&&a.dims.length!==0;if(g&&i.dims.length===4&&i.dims[0]===l&&i.dims[1]!==t.kvNumHeads&&i.dims[2]===t.kvNumHeads&&i.dims[3]===y)throw new Error("BSNH pastKey/pastValue is not supported");if(g&&x){if(i.dims.length!==4)throw new Error('Input "past_key" is expected to have 4 dimensions');if(a.dims.length!==4)throw new Error('Input "past_value" is expected to have 4 dimensions');h=i.dims[2]}else if(g||x)throw new Error('Input "past_key" and "past_value" shall be both present or both absent');let v=1;if(n&&n.dims.length>0){if(r.dims.length!==3)throw new Error('Input "query" is expected to have 3 dimensions when key is given');if(n.dims.length<3||n.dims.length>5)throw new Error('Input "key" is expected to have 3, 4, or 5 dimensions');if(r.dims[0]!==n.dims[0])throw new Error('Input "query" and "key" shall have same dim 0 (batch size)');if(n.dims.length===3){if(r.dims[2]%n.dims[2]!==0)throw new Error('Dimension 2 of "query" should be a multiple of "key"');u=n.dims[1]}else if(n.dims.length===5){if(n.dims[2]!==t.numHeads||n.dims[3]!==2||n.dims[4]!==y)throw new Error('Expect "key" shape (batch_size, kv_sequence_length, num_heads, 2, head_size) for packed kv');if(o)throw new Error('Expect "value" be none when "key" has packed kv format.');u=n.dims[1]}else{if(n.dims[1]!==t.numHeads||n.dims[3]!==y)throw new Error('Expect "key" shape (batch_size, num_heads, kv_sequence_length, head_size) for past_key');u=n.dims[2]}}else{if(r.dims.length!==3&&r.dims.length!==5)throw new Error('Input "query" is expected to have 3 or 5 dimensions when key is empty');if(r.dims.length===5&&(r.dims[2]!==t.numHeads||r.dims[3]!==3))throw new Error('Expect "query" shape (batch_size, kv_sequence_length, num_heads, 3, head_size) for packed kv');v=3}let S=0,T=!1,A=t.kvNumHeads?y*t.kvNumHeads:m;if(o&&o.dims.length>0){if(o.dims.length!==3&&o.dims.length!==4)throw new Error('Input "value" is expected to have 3 or 4 dimensions');if(r.dims[0]!==o.dims[0])throw new Error('Input "query" and "value" shall have same dim 0 (batch_size)');if(o.dims.length===3){if(u!==o.dims[1])throw new Error('Input "key" and "value" shall have the same dim 1 (kv_sequence_length)');A=o.dims[2]}else{if(u!==o.dims[2])throw new Error('Input "past_key" and "past_value" shall have the same dim 2 (kv_sequence_length)');A=o.dims[1]*o.dims[3],T=!0}}let C=e.length>4?e[5]:void 0;if(C&&C.dims.length!==1&&C.dims[0]!==l)throw new Error('Input "seqlens" is expected to have 1 dimension and the same dim 0 as batch_size');let P=-1,D=-1,R=!1;return{batchSize:l,sequenceLength:p,pastSequenceLength:h,kvSequenceLength:u,totalSequenceLength:P,maxSequenceLength:D,inputHiddenSize:0,hiddenSize:m,vHiddenSize:A,headSize:y,vHeadSize:Math.floor(A/t.kvNumHeads),numHeads:t.numHeads,kvNumHeads:t.kvNumHeads,nReps:t.numHeads/t.kvNumHeads,pastPresentShareBuffer:!1,maskType:S,scale:t.scale,broadcastResPosBias:R,passPastInKv:T,qkvFormat:v}},ih=ee({perm:[0,2,1,3]}),Gd=(e,t,r)=>{let n=t,o=r.kvNumHeads;return t.dims.length===3&&r.kvSequenceLength!==0&&(n=t.reshape([r.batchSize,r.kvSequenceLength,o,r.headSize]),n=e.compute(Pe(n,ih.perm),{inputs:[n],outputs:[-1]})[0]),n},Hd=(e,t)=>{let r=oh(e.inputs,t);if(e.inputs[0].dims.length===5)throw new Error("Packed QKV is not implemented");if(e.inputs[1]?.dims.length===5)throw new Error("Packed KV is not implemented");let n=e.inputs[0],o=e.inputs[1]&&e.inputs[1].dims.length>0?e.inputs[1]:void 0,i=e.inputs[2]&&e.inputs[2].dims.length>0?e.inputs[2]:void 0,a=e.inputs[3]&&e.inputs[3].dims.length!==0?e.inputs[3]:void 0,d=e.inputs[4]&&e.inputs[4].dims.length!==0?e.inputs[4]:void 0,l=e.inputs.length>4?e.inputs[5]:void 0,p=e.inputs.length>5?e.inputs[6]:void 0,m=r.kvNumHeads?r.kvNumHeads:r.numHeads,u=ee({axis:2,numOutputs:3,splitSizes:[r.numHeads*r.headSize,m*r.headSize,m*r.headSize]}),[h,_,y]=!o&&!i?e.compute(So([n],u),{inputs:[n],outputs:[-1,-1,-1]}):[n,o,i],g=er(e,r.batchSize,r.numHeads,r.sequenceLength,r.headSize,h,void 0,0);Ut(e,g,Gd(e,_,r),Gd(e,y,r),void 0,void 0,a,d,void 0,r,l,p)}});var qd,ah,sh,Kd,jd=U(()=>{"use strict";J();ne();dt();ae();qd=(e,t,r,n,o,i,a,d)=>{let l=me(i),p=l===1?"f32":`vec${l}f`,m=l===1?"vec2f":`mat2x${l}f`,u=o*a,h=64;u===1&&(h=256);let _=[o,a,i/l],y=[o,a,2],g=["rank","type","type"],x=[];x.push(...N(_,y));let $=v=>{let S=E("x",t.dataType,3,l),T=E("scale",r.dataType,r.dims),A=E("bias",n.dataType,n.dims),C=M("output",1,3,2),P=[S,T,A,C];return`
  var<workgroup> workgroup_shared : array<${m}, ${h}>;
  const workgroup_size = ${h}u;
  ${v.declareVariables(...P)}
  ${v.mainStart(h)}
    let batch = workgroup_index / uniforms.x_shape[1];
    let channel = workgroup_index % uniforms.x_shape[1];
    let hight = uniforms.x_shape[2];
    // initialize workgroup memory
    var sum = ${p}(0);
    var squared_sum = ${p}(0);
    for (var h = local_idx; h < hight; h += workgroup_size) {
      let value = ${p}(${S.get("batch","channel","h")});
      sum += value;
      squared_sum += value * value;
    }
    workgroup_shared[local_idx] = ${m}(sum, squared_sum);
    workgroupBarrier();

    for (var currSize = workgroup_size >> 1;  currSize > 0; currSize = currSize >> 1) {
      if (local_idx < currSize) {
        workgroup_shared[local_idx] = workgroup_shared[local_idx] + workgroup_shared[local_idx + currSize];
      }
      workgroupBarrier();
    }
    if (local_idx == 0) {
      let sum_final = ${qe("workgroup_shared[0][0]",l)} / f32(hight * ${l});
      let squared_sum_final = ${qe("workgroup_shared[0][1]",l)} / f32(hight * ${l});

      let inv_std_dev = inverseSqrt(squared_sum_final - sum_final * sum_final + f32(${d}));
      let channel_scale = inv_std_dev * f32(scale[channel]);
      let channel_shift = f32(bias[channel]) - sum_final * channel_scale;
      output[workgroup_index] = vec2f(channel_scale, channel_shift);
    }
  }`};return e.compute({name:"InstanceNormComputeChannelScaleShift",shaderCache:{hint:`${l};${d};${h}`,inputDependencies:g},getRunData:()=>({outputs:[{dims:y,dataType:1}],dispatchGroup:{x:u},programUniforms:x}),getShaderSource:$},{inputs:[t,r,n],outputs:[-1]})[0]},ah=(e,t,r)=>{let n=t[0].dims,o=n,i=2,a=n[0],d=n[1],l=k.sizeFromDimension(n,i),p=me(l),m=k.size(o)/p,u=qd(e,t[0],t[1],t[2],a,l,d,r.epsilon),h=[a,d,l/p],_=[a,d],y=["type","none"],g=x=>{let $=E("x",t[0].dataType,h.length,p),v=E("scale_shift",1,_.length,2),S=M("output",t[0].dataType,h.length,p),T=[$,v,S];return`
  ${x.registerUniform("output_size","u32").declareVariables(...T)}
  ${x.mainStart()}
  ${x.guardAgainstOutOfBoundsWorkgroupSizes("uniforms.output_size")}
      let outputIndices = ${S.offsetToIndices("global_idx")};
      let batch = outputIndices[0];
      let channel = outputIndices[1];
      let scale_shift = ${v.getByIndices("vec2<u32>(batch, channel)")};
      let value = ${$.getByOffset("global_idx")} * ${S.type.value}(scale_shift.x) + ${S.type.value}(scale_shift.y);
      ${S.setByOffset("global_idx","value")};
  }`};e.compute({name:"InstanceNormalization",shaderCache:{hint:`${p}`,inputDependencies:y},getRunData:()=>({outputs:[{dims:o,dataType:t[0].dataType}],dispatchGroup:{x:Math.ceil(m/64)},programUniforms:[{type:12,data:m},...N(h,_,h)]}),getShaderSource:g},{inputs:[t[0],u]})},sh=(e,t,r)=>{let n=t[0].dims,o=n,i=n[0],a=n[n.length-1],d=k.sizeFromDimension(n,1)/a,l=me(a),p=k.size(o)/l,m=[{type:12,data:d},{type:12,data:Math.floor(a/l)}],u=["type","type"],h=!1,_=[0,n.length-1];for(let $=0;$<n.length-2;$++)h=h||n[$+1]!==1,_.push($+1);h=h&&n[n.length-1]!==1;let y=h?e.compute(Pe(e.inputs[0],_),{inputs:[e.inputs[0]],outputs:[-1]})[0]:e.inputs[0].reshape(Array.from({length:n.length},($,v)=>n[_[v]])),g=qd(e,y,t[1],t[2],i,d,a,r.epsilon),x=$=>{let v=ye(t[0].dataType),S=l===1?"vec2f":`mat${l}x2f`,T=P=>{let D=P===0?"x":"y",R=l===1?"f32":`vec${l}f`;switch(l){case 1:return`${v}(${R}(scale.${D}))`;case 2:return`vec2<${v}>(${R}(scale[0].${D}, scale[1].${D}))`;case 4:return`vec4<${v}>(${R}(scale[0].${D}, scale[1].${D}, scale[2].${D}, scale[3].${D}))`;default:throw new Error(`Not supported compoents ${l}`)}},A=E("input",t[0].dataType,t[0].dims,l),C=M("output",t[0].dataType,o,l);return`
  @group(0) @binding(0) var<storage, read> input : array<${A.type.storage}>;
  @group(0) @binding(1) var<storage, read> scale_input : array<${S}>;
  @group(0) @binding(2) var<storage, read_write> output : array<${C.type.storage}>;
  struct Uniforms {H: u32, C : u32};
  @group(0) @binding(3) var<uniform> uniforms: Uniforms;

  ${$.mainStart()}
    let current_image_number = global_idx / (uniforms.C * uniforms.H);
    let current_channel_number = global_idx % uniforms.C;

    let scale_offset = current_image_number * uniforms.C + current_channel_number;
    let scale = scale_input[scale_offset];
    output[global_idx] = fma(input[global_idx], ${T(0)}, ${T(1)});
  }`};e.compute({name:"InstanceNormalizationNHWC",shaderCache:{hint:`${l}`,inputDependencies:u},getRunData:()=>({outputs:[{dims:o,dataType:t[0].dataType}],dispatchGroup:{x:Math.ceil(p/64)},programUniforms:m}),getShaderSource:x},{inputs:[t[0],g]})},Kd=(e,t)=>{t.format==="NHWC"?sh(e,e.inputs,t):ah(e,e.inputs,t)}});var uh,dh,Yd,Zd=U(()=>{"use strict";J();ne();ae();uh=e=>{if(!e||e.length<2)throw new Error("layerNorm requires at least 2 inputs.")},dh=(e,t,r)=>{let n=t.simplified,o=e[0].dims,i=e[1],a=!n&&e[2],d=o,l=k.normalizeAxis(t.axis,o.length),p=k.sizeToDimension(o,l),m=k.sizeFromDimension(o,l),u=k.size(i.dims),h=a?k.size(a.dims):0;if(u!==m||a&&h!==m)throw new Error(`Size of X.shape()[axis:] == ${m}.
       Size of scale and bias (if provided) must match this.
       Got scale size of ${u} and bias size of ${h}`);let _=[];for(let A=0;A<o.length;++A)A<l?_.push(o[A]):_.push(1);let y=me(m),g=["type","type"],x=[{type:12,data:p},{type:1,data:m},{type:12,data:Math.floor(m/y)},{type:1,data:t.epsilon}];a&&g.push("type");let $=r>1,v=r>2,S=A=>{let C=ye(e[0].dataType),P=[E("x",e[0].dataType,e[0].dims,y),E("scale",i.dataType,i.dims,y)];a&&P.push(E("bias",a.dataType,a.dims,y)),P.push(M("output",e[0].dataType,d,y)),$&&P.push(M("mean_data_output",1,_)),v&&P.push(M("inv_std_output",1,_));let D=[{name:"norm_count",type:"u32"},{name:"norm_size",type:"f32"},{name:"norm_size_vectorized",type:"u32"},{name:"epsilon",type:"f32"}];return`
  ${A.registerUniforms(D).declareVariables(...P)}
  ${A.mainStart()}
    ${A.guardAgainstOutOfBoundsWorkgroupSizes("uniforms.norm_count")}
    let offset = global_idx * uniforms.norm_size_vectorized;
    var mean_vector = ${so("f32",y)};
    var mean_square_vector = ${so("f32",y)};

    for (var h: u32 = 0u; h < uniforms.norm_size_vectorized; h++) {
      let value = ${Pt(C,y,"x[h + offset]")};
      mean_vector += value;
      mean_square_vector += value * value;
    }
    let mean = ${qe("mean_vector",y)} / uniforms.norm_size;
    let inv_std_dev = inverseSqrt(${qe("mean_square_vector",y)} / uniforms.norm_size ${n?"":"- mean * mean"} + uniforms.epsilon);

    for (var j: u32 = 0; j < uniforms.norm_size_vectorized; j++) {
      let f32input = ${Pt(C,y,"x[j + offset]")};
      let f32scale = ${Pt(C,y,"scale[j]")};
      output[j + offset] = ${P[0].type.value}((f32input ${n?"":"- mean"}) * inv_std_dev * f32scale
        ${a?`+ ${Pt(C,y,"bias[j]")}`:""}
      );
    }

    ${$?"mean_data_output[global_idx] = mean":""};
    ${v?"inv_std_output[global_idx] = inv_std_dev":""};
  }`},T=[{dims:d,dataType:e[0].dataType}];return $&&T.push({dims:_,dataType:1}),v&&T.push({dims:_,dataType:1}),{name:"LayerNormalization",shaderCache:{hint:`${y};${r};${n}`,inputDependencies:g},getRunData:()=>({outputs:T,dispatchGroup:{x:Math.ceil(p/64)},programUniforms:x}),getShaderSource:S}},Yd=(e,t)=>{uh(e.inputs),e.compute(dh(e.inputs,t,e.outputCount))}});var lh,Qd,Xd=U(()=>{"use strict";ne();Zr();Qr();lh=e=>{if(!e||e.length!==2)throw new Error("MatMul requires 2 inputs.");if(e[0].dims[e[0].dims.length-1]!==e[1].dims[e[1].dims.length-2])throw new Error("shared dimension does not match.")},Qd=e=>{lh(e.inputs);let t=tt.calcShape(e.inputs[0].dims,e.inputs[1].dims,!0);if(!t)throw new Error("Can't use matmul on the given tensors");let r=t[t.length-1],n=e.inputs[0].dims[e.inputs[0].dims.length-1];if(r<8&&n<8)e.compute(Yr(e.inputs,{activation:""},t));else{let o=t[t.length-2],i=k.size(e.inputs[0].dims.slice(0,-2)),a=k.size(e.inputs[1].dims.slice(0,-2));if(i!==1&&o===1&&a===1){let d=e.inputs[0].reshape([1,i,n]),l=e.inputs[1].reshape([1,n,r]),p=[1,i,r],m=[d,l];e.compute(Jt(m,{activation:""},t,p),{inputs:m})}else e.compute(Jt(e.inputs,{activation:""},t))}}});var ch,ph,mh,Jd,el,tl=U(()=>{"use strict";J();ne();xe();ae();ch=(e,t)=>{if(e.length<3||e.length>4)throw new Error("MatMulNBits requires 3 or 4 inputs");let r=e[0],n=r.dims.length;if(r.dims[n-1]!==t.k)throw new Error("The last dim of input shape does not match the k value");let o=Math.floor((t.k+t.blockSize-1)/t.blockSize),i=t.blockSize/8*t.bits,a=e[1];if(!k.areEqual(a.dims,[t.n,o,i]))throw new Error("The second inputs must be 3D tensor with shape N X nBlocksPerCol X blobSize");let l=e[2].dims;if(k.size(l)!==t.n*o)throw new Error("scales input size error.");if(e.length===4){let m=e[3].dims,u=t.bits>4?t.n*o:t.n*Math.floor((o+1)/2);if(k.size(m)!==u)throw new Error("zeroPoints input size error.")}},ph=(e,t)=>{let r=e[0].dims,n=r.length,o=r[n-2],i=t.k,a=t.n,d=r.slice(0,n-2),l=k.size(d),m=e[1].dims[2]/4,u=e[0].dataType,h=me(t.k),_=me(m),y=me(a),g=d.concat([o,a]),x=o>1&&a/y%2===0?2:1,$=k.size(g)/y/x,v=64,S=[],T=[l,o,i/h],A=k.convertShape(e[1].dims).slice();A.splice(-1,1,m/_),S.push(...N(T)),S.push(...N(A)),S.push(...N(e[2].dims)),e.length===4&&S.push(...N(k.convertShape(e[3].dims)));let C=[l,o,a/y];S.push(...N(C));let P=D=>{let R=T.length,H=E("a",e[0].dataType,R,h),L=E("b",12,A.length,_),re=E("scales",e[2].dataType,e[2].dims.length),V=[H,L,re],K=e.length===4?E("zero_points",12,e[3].dims.length):void 0;K&&V.push(K);let we=C.length,j=M("output",e[0].dataType,we,y),Q=ye(e[0].dataType),ie=(()=>{switch(h){case 1:return`array<${Q}, 8>`;case 2:return`mat4x2<${Q}>`;case 4:return`mat2x4<${Q}>`;default:throw new Error(`${h}-component is not supported.`)}})(),te=()=>{let ve=`
          // reuse a data
            var input_offset = ${H.indicesToOffset(`${H.type.indices}(batch, row, word_offset)`)};
            var a_data: ${ie};
            for (var j: u32 = 0; j < ${8/h}; j++) {
              a_data[j] = ${H.getByOffset("input_offset")};
              input_offset++;
            }
          `;for(let de=0;de<y*x;de++)ve+=`
            b_value = ${_===1?`b${de}_data`:`b${de}_data[i]`};
            b_value_lower = unpack4xU8(b_value & b_mask);
            b_value_upper = unpack4xU8((b_value >> 4) & b_mask);
            b_quantized_values = ${ie}(${Array.from({length:4},(W,Y)=>`${Q}(b_value_lower[${Y}]), ${Q}(b_value_upper[${Y}])`).join(", ")});
            b_dequantized_values = ${(()=>h===1?`${ie}(${Array.from({length:8},(W,Y)=>`(b_quantized_values[${Y}] - ${K?`zero_point${de}`:"zero_point"}) * scale${de}`).join(", ")});`:`(b_quantized_values - ${ie}(${Array(8).fill(`${K?`zero_point${de}`:"zero_point"}`).join(",")})) * scale${de};`)()};
            workgroup_shared[local_id.x * ${x} + ${Math.floor(de/y)}]${y>1?`[${de%y}]`:""} += ${Array.from({length:8/h},(W,Y)=>`${h===1?`a_data[${Y}] * b_dequantized_values[${Y}]`:`dot(a_data[${Y}], b_dequantized_values[${Y}])`}`).join(" + ")};
          `;return ve},be=()=>{let ve=`
            var col_index = col * ${y};
            ${K?`
            let zero_point_bytes_per_col = (nBlocksPerCol + 1) / 2;
            var zero_point_byte_count: u32;
            var zero_point_word_index: u32;
            var zero_point_byte_offset: u32;
            let zero_point_nibble_offset: u32 = block & 0x1u;
            var zero_point_bits_offset: u32;
            var zero_point_word: u32;`:`
            // The default zero point is 8 for unsigned 4-bit quantization.
            let zero_point = ${Q}(8);`}
            `;for(let de=0;de<y*x;de++)ve+=`
            let scale${de} = ${re.getByOffset("col_index * nBlocksPerCol + block")};
            ${K?`
            zero_point_byte_count = col_index * zero_point_bytes_per_col + (block >> 0x1u);
            zero_point_word_index = zero_point_byte_count >> 0x2u;
            zero_point_byte_offset = zero_point_byte_count & 0x3u;
            zero_point_bits_offset = (zero_point_byte_offset << 3) + (zero_point_nibble_offset << 2);
            zero_point_word = ${K.getByOffset("zero_point_word_index")} >> zero_point_bits_offset;
            let zero_point${de} = ${Q}((zero_point_word) & 0xFu);`:""}
            col_index += 1;`;return ve},Oe=()=>{let ve=`col_index = col * ${y};`;for(let de=0;de<y*x;de++)ve+=`
            let b${de}_data = ${L.getByIndices(`${L.type.indices}(col_index, block, word)`)};
            col_index += 1;`;return ve+=`
            var b_value: u32;
            let b_mask: u32 = 0x0F0F0F0Fu;
            var b_value_lower: vec4<u32>;
            var b_value_upper: vec4<u32>;
            var b_quantized_values: ${ie};
            var b_dequantized_values: ${ie};`,ve};return`
        var<workgroup> workgroup_shared: array<${j.type.value}, ${x*v}>;
        ${D.declareVariables(...V,j)}
        ${D.mainStart([v,1,1])}
          let output_indices = ${j.offsetToIndices(`(global_idx / ${v}) * ${x}`)};
          let col = output_indices[2];
          let row = output_indices[1];
          let batch = output_indices[0];
          let nBlocksPerCol = uniforms.b_shape[1];

          for (var block = local_id.x; block < nBlocksPerCol; block += ${v}) {
            //process one block
            var word_offset: u32 = block * ${t.blockSize/h};
            ${be()}
            for (var word: u32 = 0; word < ${m}; word += ${_}) {
              ${Oe()}
              for (var i: u32 = 0; i < ${_}; i++) {
                ${te()}
                word_offset += ${8/h};
              }
            }
          }
          workgroupBarrier();

          if (local_id.x < ${x}) {
            var output_value: ${j.type.value} = ${j.type.value}(0);
            var workgroup_shared_offset: u32 = local_id.x;
            for (var b: u32 = 0u; b < ${v}u; b++) {
              output_value += workgroup_shared[workgroup_shared_offset];
              workgroup_shared_offset += ${x};
            }
            ${j.setByIndices(`${j.type.indices}(batch, row, col + local_id.x)`,"output_value")};
          }
        }`};return{name:"MatMulNBits",shaderCache:{hint:`${t.blockSize};${t.bits};${h};${_};${y};${x};${v}`,inputDependencies:Array(e.length).fill("rank")},getRunData:()=>({outputs:[{dims:g,dataType:u}],dispatchGroup:{x:$},programUniforms:S}),getShaderSource:P}},mh=(e,t)=>{let r=e[0].dims,n=r.length,o=r[n-2],i=t.k,a=t.n,d=r.slice(0,n-2),l=k.size(d),m=e[1].dims[2]/4,u=e[0].dataType,h=me(t.k),_=me(m),y=d.concat([o,a]),g=128,x=a%8===0?8:a%4===0?4:1,$=g/x,v=$*_*8,S=v/h,T=v/t.blockSize,A=k.size(y)/x,C=[],P=[l,o,i/h],D=k.convertShape(e[1].dims).slice();D.splice(-1,1,m/_),C.push(...N(P)),C.push(...N(D)),C.push(...N(e[2].dims)),e.length===4&&C.push(...N(k.convertShape(e[3].dims)));let R=[l,o,a];C.push(...N(R));let H=L=>{let re=P.length,V=E("a",e[0].dataType,re,h),K=E("b",12,D.length,_),we=E("scales",e[2].dataType,e[2].dims.length),j=[V,K,we],Q=e.length===4?E("zero_points",12,e[3].dims.length):void 0;Q&&j.push(Q);let ie=R.length,te=M("output",e[0].dataType,ie),be=ye(e[0].dataType),Oe=()=>{switch(h){case 1:return`
          let a_data0 = vec4<${be}>(sub_a[word_offset], sub_a[word_offset + 1], sub_a[word_offset + 2], sub_a[word_offset + 3]);
          let a_data1 = vec4<${be}>(sub_a[word_offset + 4], sub_a[word_offset + 5], sub_a[word_offset + 6], sub_a[word_offset + 7]);`;case 2:return`
          let a_data0 = vec4<${be}>(sub_a[word_offset], sub_a[word_offset + 1]);
          let a_data1 = vec4<${be}>(sub_a[word_offset + 2], sub_a[word_offset + 3]);`;case 4:return`
          let a_data0 = sub_a[word_offset];
          let a_data1 = sub_a[word_offset + 1];`;default:throw new Error(`${h}-component is not supported.`)}};return`
        var<workgroup> sub_a: array<${V.type.value}, ${S}>;
        var<workgroup> inter_results: array<array<${te.type.value}, ${$}>, ${x}>;
        ${L.declareVariables(...j,te)}
        ${L.mainStart([$,x,1])}
          let output_indices = ${te.offsetToIndices(`workgroup_index * ${x}`)};
          let col = output_indices[2];
          let row = output_indices[1];
          let batch = output_indices[0];
          let n_blocks_per_col = uniforms.b_shape[1];
          let num_tiles =  (n_blocks_per_col - 1) / ${T} + 1;

          // Loop over shared dimension.
          for (var tile: u32 = 0; tile < num_tiles; tile += 1) {
            let a_col_start = tile * ${S};
            // load one tile A data into shared memory.
            for (var a_offset = local_idx; a_offset < ${S}; a_offset += ${g})
            {
              let a_col = a_col_start + a_offset;
              if (a_col < uniforms.a_shape[2])
              {
                sub_a[a_offset] = ${V.getByIndices(`${V.type.indices}(batch, row, a_col)`)};
              } else {
                sub_a[a_offset] = ${V.type.value}(0);
              }
            }
            workgroupBarrier();

            // each thread process one block
            let b_row = col + local_id.y;
            let block = tile * ${T} + local_id.x;
            ${Q?`
            let zero_point_bytes_per_col = (n_blocks_per_col + 1) / 2;
            let zero_point_byte_count = b_row * zero_point_bytes_per_col + (block >> 0x1u);
            let zero_point_word_index = zero_point_byte_count >> 0x2u;
            let zero_point_byte_offset = zero_point_byte_count & 0x3u;
            let zero_point_nibble_offset: u32 = block & 0x1u;
            let zero_point_bits_offset = (zero_point_byte_offset << 3) + (zero_point_nibble_offset << 2);
            let zero_point_word = ${Q.getByOffset("zero_point_word_index")} >> zero_point_bits_offset;
            let zero_point = ${be}((zero_point_word) & 0xFu);`:`
            // The default zero point is 8 for unsigned 4-bit quantization.
            let zero_point = ${be}(8);`}
            let scale = ${we.getByOffset("b_row * n_blocks_per_col + block")};
            let b_data = ${K.getByIndices(`${K.type.indices}(b_row, block, 0)`)};
            var word_offset = local_id.x * ${t.blockSize/h};
            for (var i: u32 = 0; i < ${_}; i++) {
              ${Oe()}
              let b_value = ${_===1?"b_data":"b_data[i]"};
              let b_value_lower = unpack4xU8(b_value & 0x0F0F0F0Fu);
              let b_value_upper = unpack4xU8((b_value >> 4) & 0x0F0F0F0Fu);
              let b_quantized_values = mat2x4<${be}>(${Array.from({length:4},(ve,de)=>`${be}(b_value_lower[${de}]), ${be}(b_value_upper[${de}])`).join(", ")});
              let b_dequantized_values = (b_quantized_values - mat2x4<${be}>(${Array(8).fill("zero_point").join(",")})) * scale;
              inter_results[local_id.y][local_id.x] += ${Array.from({length:2},(ve,de)=>`${`dot(a_data${de}, b_dequantized_values[${de}])`}`).join(" + ")};
              word_offset += ${8/h};
            }
            workgroupBarrier();
          }

          if (local_idx < ${x}) {
            var output_value: ${te.type.value} = ${te.type.value}(0);
            for (var b = 0u; b < ${$}; b++) {
              output_value += inter_results[local_idx][b];
            }
            if (col + local_idx < uniforms.output_shape[2])
            {
              ${te.setByIndices(`${te.type.indices}(batch, row, col + local_idx)`,"output_value")}
            }
          }
        }`};return{name:"BlockwiseMatMulNBits32",shaderCache:{hint:`${t.blockSize};${h};${_};${$};${x}`,inputDependencies:Array(e.length).fill("rank")},getRunData:()=>({outputs:[{dims:y,dataType:u}],dispatchGroup:{x:A},programUniforms:C}),getShaderSource:H}},Jd=(e,t)=>{ch(e.inputs,t),t.blockSize===32&&e.adapterInfo.isVendor("intel")&&e.adapterInfo.isArchitecture("gen-12lp")?e.compute(mh(e.inputs,t)):e.compute(ph(e.inputs,t))},el=e=>ee(e)});var fh,hh,gh,bh,yh,_h,wh,vh,rl,nl=U(()=>{"use strict";J();ne();ae();fh=e=>{if(!e||e.length<1)throw new Error("Too few inputs");if(e[0].dataType!==1&&e[0].dataType!==10)throw new Error("Input type must be float or float16.");if(e.length>=2){let t=e[0].dims.length*2===e[1].dims[0];if(e.length===4&&(t=e[3].dims[0]*2===e[1].dims[0]),!t)throw new Error("The pads should be a 1D tensor of shape [2 * input_rank] or [2 * num_axes].")}},hh=(e,t,r)=>{let n="";for(let o=t-1;o>=0;--o)n+=`
            k = i32(${e.indicesGet("indices",o)}) - ${q("uniforms.pads",o,r)};
            if (k < 0) {
              break;
            }
            if (k >= i32(${q("uniforms.x_shape",o,t)})) {
              break;
            }
            offset += k * i32(${q("uniforms.x_strides",o,t)});
        `;return`
          value = ${e.type.value}(uniforms.constant_value);
          for (var i = 0; i < 1; i++) {
            var offset = 0;
            var k = 0;
            ${n}
            value = x[offset];
          }
      `},gh=(e,t,r)=>{let n="";for(let o=t-1;o>=0;--o)n+=`
                k = i32(${e.indicesGet("indices",o)}) - ${q("uniforms.pads",o,r)};
                if (k < 0) {
                  k = -k;
                }
                {
                  let _2n_1 = 2 * (i32(${q("uniforms.x_shape",o,t)}) - 1);
                  k = k % _2n_1;
                  if(k >= i32(${q("uniforms.x_shape",o,t)})) {
                    k = _2n_1 - k;
                  }
                }
                offset += k * i32(${q("uniforms.x_strides",o,t)});
            `;return`
              var offset = 0;
              var k = 0;
              ${n}
              value = x[offset];
          `},bh=(e,t,r)=>{let n="";for(let o=t-1;o>=0;--o)n+=`
                k = i32(${e.indicesGet("indices",o)}) - ${q("uniforms.pads",o,r)};
                if (k < 0) {
                  k = 0;
                }
                if (k >= i32(${q("uniforms.x_shape",o,t)})) {
                  k = i32(${q("uniforms.x_shape",o,t)}) - 1;
                }
                offset += k * i32(${q("uniforms.x_strides",o,t)});
            `;return`
              var offset = 0;
              var k = 0;
              ${n}
              value = x[offset];
          `},yh=(e,t,r)=>{let n="";for(let o=t-1;o>=0;--o)n+=`
                k = i32(${e.indicesGet("indices",o)}) - ${q("uniforms.pads",o,r)};
                if (k < 0)  {
                  k += i32(${q("uniforms.x_shape",o,t)}]);
                }
                if (k >= i32(${q("uniforms.x_shape",o,t)})) {
                  k -= i32(${q("uniforms.x_shape",o,t)});
                }
                offset += k * i32(${q("uniforms.x_strides",o,t)});
            `;return`
              var offset = 0;
              var k = 0;
              ${n}
              value = x[offset];
          `},_h=(e,t,r)=>{switch(r.mode){case 0:return hh(e,t,r.pads.length);case 1:return gh(e,t,r.pads.length);case 2:return bh(e,t,r.pads.length);case 3:return yh(e,t,r.pads.length);default:throw new Error("Invalid mode")}},wh=(e,t)=>{let r=k.padShape(e[0].dims.slice(),t.pads),n=e[0].dims,o=k.size(r),i=[{type:12,data:o},{type:6,data:t.pads}],a=e.length>=3&&e[2].data;t.mode===0&&i.push({type:a?e[2].dataType:1,data:t.value}),i.push(...N(e[0].dims,r));let d=["rank"],l=p=>{let m=M("output",e[0].dataType,r.length),u=E("x",e[0].dataType,n.length),h=u.type.value,_=_h(m,n.length,t),y=[{name:"output_size",type:"u32"},{name:"pads",type:"i32",length:t.pads.length}];return t.mode===0&&y.push({name:"constant_value",type:a?h:"f32"}),`
            ${p.registerUniforms(y).declareVariables(u,m)}
            ${p.mainStart()}
            ${p.guardAgainstOutOfBoundsWorkgroupSizes("uniforms.output_size")}

            let indices = ${m.offsetToIndices("global_idx")};

            var value = ${h}(0);
            ${_}
            output[global_idx] = value;
        }`};return{name:"Pad",shaderCache:{hint:`${t.mode}${a}`,inputDependencies:d},getRunData:()=>({outputs:[{dims:r,dataType:e[0].dataType}],dispatchGroup:{x:Math.ceil(k.size(r)/64)},programUniforms:i}),getShaderSource:l}},vh=(e,t)=>{if(e.length>1){let r=e[1].getBigInt64Array(),n=e.length>=3&&e[2].data?e[2].dataType===10?e[2].getUint16Array()[0]:e[2].getFloat32Array()[0]:0,o=e[0].dims.length,i=new Int32Array(2*o).fill(0);if(e.length>=4){let d=e[3].getBigInt64Array();for(let l=0;l<d.length;l++)i[Number(d[l])]=Number(r[l]),i[Number(d[l])+o]=Number(r[l+d.length])}else r.forEach((d,l)=>i[Number(l)]=Number(d));let a=[];return i.forEach(d=>a.push(d)),{mode:t.mode,value:n,pads:a}}else return t},rl=(e,t)=>{fh(e.inputs);let r=vh(e.inputs,t);e.compute(wh(e.inputs,r),{inputs:[0]})}});var en,ol,il,al,sl,$h,xh,ul,dl,ll,cl,pl,ml,fl,hl,gl,bl,yl,_l,wl=U(()=>{"use strict";Le();J();ne();ae();en=e=>{if(_e.webgpu.validateInputContent&&(!e||e.length!==1))throw new Error("Pool ops requires 1 input.")},ol=(e,t,r)=>{let n=t.format==="NHWC",o=e.dims.slice();n&&o.splice(1,0,o.pop());let i=Object.hasOwnProperty.call(t,"dilations"),a=t.kernelShape.slice(),d=t.strides.slice(),l=i?t.dilations.slice():[],p=t.pads.slice();kt.adjustPoolAttributes(r,o,a,d,l,p);let m=kt.computePoolOutputShape(r,o,d,l,a,p,t.autoPad),u=Object.assign({},t);i?Object.assign(u,{kernelShape:a,strides:d,pads:p,dilations:l,cacheKey:t.cacheKey}):Object.assign(u,{kernelShape:a,strides:d,pads:p,cacheKey:t.cacheKey});let h=m.slice();return h.push(h.splice(1,1)[0]),[u,n?h:m]},il=(e,t)=>{let r=t.format==="NHWC",n=k.size(e),o=k.size(t.kernelShape),i=[{type:12,data:n},{type:12,data:o}],a=[{name:"outputSize",type:"u32"},{name:"kernelSize",type:"u32"}];if(t.kernelShape.length<=2){let d=t.kernelShape[t.kernelShape.length-1],l=t.strides[t.strides.length-1],p=t.pads[t.pads.length/2-1],m=t.pads[t.pads.length-1],u=!!(p+m);i.push({type:12,data:d},{type:12,data:l},{type:12,data:p},{type:12,data:m}),a.push({name:"kw",type:"u32"},{name:"sw",type:"u32"},{name:"pwStart",type:"u32"},{name:"pwEnd",type:"u32"});let h=!1;if(t.kernelShape.length===2){let _=t.kernelShape[t.kernelShape.length-2],y=t.strides[t.strides.length-2],g=t.pads[t.pads.length/2-2],x=t.pads[t.pads.length-2];h=!!(g+x),i.push({type:12,data:_},{type:12,data:y},{type:12,data:g},{type:12,data:x}),a.push({name:"kh",type:"u32"},{name:"sh",type:"u32"},{name:"phStart",type:"u32"},{name:"phEnd",type:"u32"})}return[i,a,!0,u,h]}else{if(r)throw new Error("Pooling with kernelShape.length > 2 is not supported for NHWC format.");let d=k.computeStrides(t.kernelShape);i.push({type:12,data:d},{type:12,data:t.pads},{type:12,data:t.strides}),a.push({name:"kernelStrides",type:"u32",length:d.length},{name:"pads",type:"u32",length:t.pads.length},{name:"strides",type:"u32",length:t.strides.length});let l=t.pads.reduce((p,m)=>p+m);return[i,a,!!l,!1,!1]}},al=(e,t,r,n,o,i,a,d,l,p,m,u)=>{let h=o.format==="NHWC",_=t.type.value,y=M("output",t.type.tensor,n);if(o.kernelShape.length<=2){let g="",x="",$="",v=r-(h?2:1);if(m?g=`
                for (var i: u32 = 0u; i < uniforms.kw; i++) {
                  xIndices[${v}] = indices[${v}] * uniforms.sw - uniforms.pwStart + i;
                  if (xIndices[${v}] < 0 || xIndices[${v}]
                      >= uniforms.x_shape[${v}]) {
                    pad++;
                    continue;
                  }
                  let x_val = x[${t.indicesToOffset("xIndices")}];
                  ${i}
                }`:g=`
                for (var i: u32 = 0u; i < uniforms.kw; i++) {
                  xIndices[${v}] = indices[${v}] * uniforms.sw - uniforms.pwStart + i;
                  let x_val = x[${t.indicesToOffset("xIndices")}];
                  ${i}
                }`,o.kernelShape.length===2){let T=r-(h?3:2);u?x=`
                for (var j: u32 = 0u; j < uniforms.kh; j++) {
                  xIndices[${T}] = indices[${T}] * uniforms.sh - uniforms.phStart + j;
                  if (xIndices[${T}] < 0 || xIndices[${T}] >= uniforms.x_shape[${T}]) {
                    pad += i32(uniforms.kw);
                    continue;
                  }
              `:x=`
                for (var j: u32 = 0u; j < uniforms.kh; j++) {
                  xIndices[${T}] = indices[${T}] * uniforms.sh - uniforms.phStart + j;
                `,$=`
              }
            `}return`
            ${e.registerUniforms(l).declareVariables(t,y)}

            ${e.mainStart()}
              ${e.guardAgainstOutOfBoundsWorkgroupSizes("uniforms.outputSize")}

              let indices = ${y.offsetToIndices("global_idx")};
              var xIndices = ${y.offsetToIndices("global_idx")};

              var value = ${_}(${d});
              var pad = 0;
              ${x}
              ${g}
              ${$}
              ${a}

              output[global_idx] = value;
            }`}else{if(h)throw new Error("Pooling with kernelShape.length > 2 is not supported for NHWC format.");let g=o.kernelShape.length,x=o.pads.length,$="";return p?$=`
                if (xIndices[j] >= uniforms.x_shape[j]) {
                  pad++;
                  isPad = true;
                  break;
                }
              }
              if (!isPad) {
                let x_val = x[${t.indicesToOffset("xIndices")}];
                ${i}
              }`:$=`
              }
              let x_val = x[${t.indicesToOffset("xIndices")}];
              ${i}
            `,`
            ${e.registerUniforms(l).declareVariables(t,y)}

            ${e.mainStart()}
              ${e.guardAgainstOutOfBoundsWorkgroupSizes("uniforms.outputSize")}
              let indices = ${y.offsetToIndices("global_idx")};
              var xIndices = ${y.offsetToIndices("global_idx")};

              var offsets: array<u32, ${g}>;

              var value = ${_}(${d});
              var pad = 0;
              var isPad = false;

              for (var i: u32 = 0u; i < uniforms.kernelSize; i++) {
                var offset = i;
                for (var j = 0u; j < ${g-1}u; j++) {
                  offsets[j] = offset / ${q("uniforms.kernelStrides","j",g)};
                  offset -= offsets[j] * ${q("uniforms.kernelStrides","j",g)};
                }
                offsets[${g-1}] = offset;

                isPad = false;
                for (var j = ${r-g}u; j < ${r}u; j++) {
                  xIndices[j] = indices[j] * ${q("uniforms.strides",`j - ${r-g}u`,g)}
                    + offsets[j - ${r-g}u] - ${q("uniforms.pads","j - 2u",x)};
                  ${$}
              }
              ${a}

              output[global_idx] = value;
            }`}},sl=e=>`${e.format};${e.ceilMode};${e.autoPad};${e.kernelShape.length}`,$h=e=>`${sl(e)};${e.countIncludePad}`,xh=e=>`${sl(e)};${e.storageOrder};${e.dilations}`,ul=e=>({format:e.format,autoPad:["NOTSET","VALID","SAME_UPPER","SAME_LOWER"][e.auto_pad],ceilMode:e.ceil_mode,kernelShape:e.kernel_shape,strides:e.strides,pads:e.pads}),dl=(e,t,r,n)=>{let[o,i]=ol(t,n,r),a=E("x",t.dataType,t.dims.length),d=a.type.value,l="value += x_val;",p="";o.countIncludePad?p+=`value /= ${d}(uniforms.kernelSize);`:p+=`value /= ${d}(i32(uniforms.kernelSize) - pad);`;let[m,u,h,_,y]=il(i,o);m.push(...N(t.dims,i));let g=["rank"];return{name:e,shaderCache:{hint:`${n.cacheKey};${h};${_};${y}`,inputDependencies:g},getRunData:()=>({outputs:[{dims:i,dataType:t.dataType}],dispatchGroup:{x:Math.ceil(k.size(i)/64)},programUniforms:m}),getShaderSource:x=>al(x,a,t.dims.length,i.length,o,l,p,0,u,h,_,y)}},ll=e=>{let t=e.count_include_pad!==0,r=ul(e);if(r.ceilMode!==0)throw new Error("using ceil() in shape computation is not yet supported for AveragePool");let n={countIncludePad:t,...r,cacheKey:""};return{...n,cacheKey:$h(n)}},cl=(e,t)=>{en(e.inputs),e.compute(dl("AveragePool",e.inputs[0],!1,t))},pl={autoPad:"",ceilMode:0,countIncludePad:!1,kernelShape:[],strides:[],pads:[],storageOrder:0,dilations:[]},ml=e=>{let t=e.format;return{format:t,...pl,cacheKey:t}},fl=(e,t)=>{en(e.inputs),e.compute(dl("GlobalAveragePool",e.inputs[0],!0,t))},hl=(e,t,r,n)=>{let[o,i]=ol(t,n,r),a=`
      value = max(x_val, value);
    `,d="",l=E("x",t.dataType,t.dims.length),p=["rank"],[m,u,h,_,y]=il(i,o);return m.push(...N(t.dims,i)),{name:e,shaderCache:{hint:`${n.cacheKey};${h};${_};${y}`,inputDependencies:p},getRunData:()=>({outputs:[{dims:i,dataType:t.dataType}],dispatchGroup:{x:Math.ceil(k.size(i)/64)},programUniforms:m}),getShaderSource:g=>al(g,l,t.dims.length,i.length,o,a,d,t.dataType===10?-65504:-1e5,u,h,_,y)}},gl=(e,t)=>{en(e.inputs),e.compute(hl("MaxPool",e.inputs[0],!1,t))},bl=e=>{let t=e.storage_order,r=e.dilations,n=ul(e);if(t!==0)throw new Error("column major storage order is not yet supported for MaxPool");if(n.ceilMode!==0)throw new Error("using ceil() in shape computation is not yet supported for MaxPool");let o={storageOrder:t,dilations:r,...n,cacheKey:""};return{...o,cacheKey:xh(o)}},yl=e=>{let t=e.format;return{format:t,...pl,cacheKey:t}},_l=(e,t)=>{en(e.inputs),e.compute(hl("GlobalMaxPool",e.inputs[0],!0,t))}});var Th,Ih,vl,$l,xl=U(()=>{"use strict";J();ne();xe();ae();Th=(e,t)=>{if(e.length<2||e.length>3)throw new Error("DequantizeLinear requires 2 or 3 inputs.");if(e.length===3&&e[1].dims===e[2].dims)throw new Error("x-scale and x-zero-point must have the same shape.");if(e.length===3&&e[0].dataType!==e[2].dataType)throw new Error("x and x-zero-point must have the same data type.");if(e[0].dataType===6&&e.length>2)throw new Error("In the case of dequantizing int32 there is no zero point.");if(e[1].dims.length!==0&&e[1].dims.length!==1&&e[1].dims.length!==e[0].dims.length)throw new Error("scale input must be a scalar, a 1D tensor, or have the same rank as the input tensor.");if(e.length>2){if(e[0].dataType!==e[2].dataType)throw new Error("x and x-zero-point must have the same data type.");if(e[1].dims.length!==e[2].dims.length)throw new Error("scale and zero-point inputs must have the same rank.");if(!e[1].dims.map((r,n)=>r===e[2].dims[n]).reduce((r,n)=>r&&n,!0))throw new Error("scale and zero-point inputs must have the same shape.")}if(t.blockSize>0){if(e[1].dims.length===0||e[1].dims.length===1&&e[1].dims[0]===1)throw new Error("blockSize must be set only for block quantization.");if(!e[1].dims.map((o,i)=>i===t.axis||o===e[0].dims[i]).reduce((o,i)=>o&&i,!0))throw new Error("For block qunatization, scale input shape to match the input shape except for the axis");if(e[1].dims.length!==e[0].dims.length)throw new Error("For block qunatization the scale input rank must be the same as the x rank.");let r=e[0].dims[t.axis],n=e[1].dims[t.axis];if(t.blockSize<Math.ceil(r/n)||t.blockSize>Math.ceil(r/(n-1)-1))throw new Error("blockSize must be with in the range [ceil(dI / Si), ceil(dI / (Si - 1) - 1)].")}},Ih=(e,t)=>{let r=k.normalizeAxis(t.axis,e[0].dims.length),n=e[0].dataType,o=n===3,i=e[0].dims,a=e[1].dataType,d=k.size(i),l=n===3||n===2,p=l?[Math.ceil(k.size(e[0].dims)/4)]:e[0].dims,m=e[1].dims,u=e.length>2?e[2]:void 0,h=u?l?[Math.ceil(k.size(u.dims)/4)]:u.dims:void 0,_=m.length===0||m.length===1&&m[0]===1,y=_===!1&&m.length===1,g=me(d),x=_&&(!l||g===4),$=x?g:1,v=x&&!l?g:1,S=E("input",l?12:n,p.length,v),T=E("scale",a,m.length),A=u?E("zero_point",l?12:n,h.length):void 0,C=M("output",a,i.length,$),P=[S,T];A&&P.push(A);let D=[p,m];u&&D.push(h);let R=[{type:12,data:d/$},{type:12,data:r},{type:12,data:t.blockSize},...N(...D,i)],H=L=>{let re=[{name:"output_size",type:"u32"},{name:"axis",type:"u32"},{name:"block_size",type:"u32"}];return`
      ${L.registerUniforms(re).declareVariables(...P,C)}
      ${L.mainStart()}
          ${L.guardAgainstOutOfBoundsWorkgroupSizes("uniforms.output_size")}
          let output_indices = ${C.offsetToIndices("global_idx")};

          // Set input x
          ${(()=>l?`
            let input = ${S.getByOffset("global_idx / 4")};
            let x_vec = ${o?"unpack4xI8(input)":"unpack4xU8(input)"};
            let x_value = ${$===1?"x_vec[global_idx % 4]":"x_vec"};`:`let x_value = ${S.getByOffset("global_idx")};`)()};

          // Set scale input
          ${(()=>_?`let scale_value= ${T.getByOffset("0")}`:y?`
            let scale_index = ${C.indicesGet("output_indices","uniforms.axis")};
            let scale_value= ${T.getByOffset("scale_index")};`:`
            var scale_indices: ${T.type.indices} = output_indices;
            let index = ${T.indicesGet("scale_indices","uniforms.axis")} / uniforms.block_size;
            ${T.indicesSet("scale_indices","uniforms.axis","index")};
            let scale_value= ${T.getByIndices("scale_indices")};`)()};

          // Set zero-point input
          ${(()=>A?_?l?`
                let zero_point_input = ${A.getByOffset("0")};
                let zero_point_vec =  ${o?"unpack4xI8(zero_point_input)":"unpack4xU8(zero_point_input)"};
                let zero_point_value= zero_point_vec[0]`:`let zero_point_value = ${A.getByOffset("0")}`:y?l?`
                let zero_point_index = ${C.indicesGet("output_indices","uniforms.axis")};
                let zero_point_input = ${A.getByOffset("zero_point_index / 4")};
                let zero_point_vec =  ${o?"unpack4xI8(zero_point_input)":"unpack4xU8(zero_point_input)"};
                let zero_point_value = zero_point_vec[zero_point_index % 4]`:`
                let zero_point_index = ${C.indicesGet("output_indices","uniforms.axis")};
                let zero_point_value = ${A.getByOffset("zero_point_index")};`:l?`
                let zero_point_offset = ${T.indicesToOffset("scale_indices")};
                let zero_point_input = ${A.getByOffset("zero_point_offset / 4")};
                let zero_point_vec = ${o?"unpack4xI8(zero_point_input)":"unpack4xU8(zero_point_input)"};
                let zero_point_value = zero_point_vec[zero_point_offset % 4];`:`let zero_point_value = ${A.getByIndices("scale_indices")};`:`let zero_point_value = ${l?o?"i32":"u32":S.type.value}(0);`)()};
      // Compute and write output
      ${C.setByOffset("global_idx",`${C.type.value}(x_value - zero_point_value) * scale_value`)};
      }`};return{name:"DequantizeLinear",shaderCache:{hint:t.cacheKey,inputDependencies:A?["rank","rank","rank"]:["rank","rank"]},getShaderSource:H,getRunData:()=>({outputs:[{dims:i,dataType:a}],dispatchGroup:{x:Math.ceil(d/$/64),y:1,z:1},programUniforms:R})}},vl=(e,t)=>{Th(e.inputs,t),e.compute(Ih(e.inputs,t))},$l=e=>ee({axis:e.axis,blockSize:e.blockSize})});var Ch,Ah,Sl,Tl=U(()=>{"use strict";Le();J();ae();Ch=(e,t,r)=>{let n=e===t,o=e<t&&r<0,i=e>t&&r>0;if(n||o||i)throw new Error("Range these inputs' contents are invalid.")},Ah=(e,t,r,n)=>{let o=Math.abs(Math.ceil((t-e)/r)),i=[o],a=o,d=[{type:12,data:a},{type:n,data:e},{type:n,data:r},...N(i)],l=p=>{let m=M("output",n,i.length),u=m.type.value,h=[{name:"outputSize",type:"u32"},{name:"start",type:u},{name:"delta",type:u}];return`
        ${p.registerUniforms(h).declareVariables(m)}
        ${p.mainStart()}
        ${p.guardAgainstOutOfBoundsWorkgroupSizes("uniforms.outputSize")}
        output[global_idx] = uniforms.start + ${u}(global_idx) * uniforms.delta;
      }`};return{name:"Range",shaderCache:{hint:`${n}`},getShaderSource:l,getRunData:()=>({outputs:[{dims:i,dataType:n}],dispatchGroup:{x:Math.ceil(a/64)},programUniforms:d})}},Sl=e=>{let t=0,r=0,n=0;e.inputs[0].dataType===6?(t=e.inputs[0].getInt32Array()[0],r=e.inputs[1].getInt32Array()[0],n=e.inputs[2].getInt32Array()[0]):e.inputs[0].dataType===1&&(t=e.inputs[0].getFloat32Array()[0],r=e.inputs[1].getFloat32Array()[0],n=e.inputs[2].getFloat32Array()[0]),_e.webgpu.validateInputContent&&Ch(t,r,n),e.compute(Ah(t,r,n,e.inputs[0].dataType),{inputs:[]})}});var kh,Eh,Il,Cl,Al=U(()=>{"use strict";J();ne();xe();ae();kh=(e,t,r,n)=>{if(e!=="none"&&n!=="i32"&&n!=="u32"&&n!=="f32")throw new Error(`Input ${n} is not supported with reduction ${e}.`);let o=`{
                var oldValue = 0;
                loop {
                  let newValueF32 =`,i=`;
                  let newValue = bitcast<i32>(newValueF32);
                  let res = atomicCompareExchangeWeak(&${t}, oldValue, newValue);
                  if res.exchanged {
                    break;
                  }
                  oldValue = res.old_value;
                }
              }`;switch(e){case"none":return`${t}=${r};`;case"add":return n==="i32"||n==="u32"?`atomicAdd(&${t}, bitcast<${n}>(${r}));`:`
              ${o}bitcast<${n}>(oldValue) + (${r})${i}`;case"max":return n==="i32"||n==="u32"?`atomicMax(&${t}, bitcast<${n}>(${r}));`:`
                ${o}max(bitcast<f32>(oldValue), (${r}))${i}`;case"min":return n==="i32"||n==="u32"?`atomicMin(&${t}, bitcast<${n}>(${r}));`:`${o}min(bitcast<${n}>(oldValue), (${r}))${i}`;case"mul":return`${o}(bitcast<${n}>(oldValue) * (${r}))${i}`;default:throw new Error(`Reduction ${e} is not supported.`)}},Eh=(e,t)=>{let r=e[0].dims,n=e[1].dims,o=r,i=1,a=Math.ceil(k.size(n)/i),d=n[n.length-1],l=k.sizeFromDimension(r,d),p=[{type:12,data:a},{type:12,data:d},{type:12,data:l},...N(e[1].dims,e[2].dims,o)],m=u=>{let h=E("indices",e[1].dataType,e[1].dims.length),_=E("updates",e[2].dataType,e[2].dims.length,i),y=t.reduction!=="none"&&t.reduction!==""?ts("output",e[0].dataType,o.length):M("output",e[0].dataType,o.length,i);return`
      ${u.registerUniform("output_size","u32").registerUniform("last_index_dimension","u32").registerUniform("num_updates_elements","u32").declareVariables(h,_,y)}
      ${u.mainStart()}
        ${u.guardAgainstOutOfBoundsWorkgroupSizes("uniforms.output_size")}
  var data_offset = 0u;
  let indices_start = uniforms.last_index_dimension * global_idx;
  let indices_end = indices_start + uniforms.last_index_dimension;
  for (var i = indices_start; i < indices_end; i++) {
    var index = i32(indices[i].x);
    ${e[0].dims.length===1?`
    let element_count_dim = uniforms.output_strides;
    let dim_value = uniforms.output_shape;`:`
    let element_count_dim = uniforms.output_strides[i - indices_start];
    let dim_value = uniforms.output_shape[i - indices_start + uniforms.last_index_dimension];`}
    if (index >= 0) {
      if (index >= i32(dim_value)) {
        index = i32(dim_value - 1);
      }
    } else {
      if (index < -i32(dim_value)) {
        index = 0;
      } else {
        index += i32(dim_value);
      }
    }
    data_offset += u32((u32(index) * element_count_dim));
  }

  for (var i = 0u; i < uniforms.num_updates_elements; i++) {
    let value = updates[uniforms.num_updates_elements * global_idx + i];
    ${kh(t.reduction,"output[data_offset + i]","value",y.type.value)}
  }

      }`};return{name:"ScatterND",shaderCache:{hint:`${t.cacheKey}_${t.reduction}`,inputDependencies:["rank","rank"]},getRunData:()=>({outputs:[{dims:o,dataType:e[0].dataType}],dispatchGroup:{x:Math.ceil(a/64)},programUniforms:p}),getShaderSource:m}},Il=e=>ee({reduction:e.reduction}),Cl=(e,t)=>{e.compute(Eh(e.inputs,t),{inputs:[e.inputs[1],e.inputs[2]],outputs:[]})}});var Ph,zh,Oh,kl,Dh,Bh,Mh,Rh,Uh,Nh,Vh,Wh,El,Lh,Gh,Hh,Fh,qh,Pl,zl,Ol=U(()=>{"use strict";J();ne();xe();ae();Ph=(e,t)=>{if(e.every(r=>r>0||(()=>{throw new Error("Resize requires scales input values to be positive")})),e.length>0){if(t.mode==="linear"){if(!(e.length===2||e.length===3||e.length===4&&e[0]===1&&e[1]===1||e.length===4&&e[0]===1&&e[3]===1||e.length===5&&e[0]===1&&e[1]===1))throw new Error(`For linear mode, Resize requires scales to be 2D, 3D, 4D with either two outermost or one innermost and
            one outermost scale values equal to 1, or 5D with two outermost scale values equal to 1`)}else if(t.mode==="cubic"&&!(e.length===2||e.length===4&&e[0]===1&&e[1]===1||e.length===4&&e[0]===1&&e[3]===1))throw new Error("Resize requires scales input size to be 2 or 4 for cubic mode")}},zh=(e,t,r)=>{t.every(o=>o>=0&&o<r||(()=>{throw new Error("Resize requires axes input values to be positive and less than rank")}));let n=new Array(r).fill(1);return t.forEach((o,i)=>n[o]=e[i]),n},Oh=(e,t,r,n,o,i)=>{let[a,d,l]=r>10?[1,2,3]:[-1,e.length>1?1:-1,-1],p=e[0].dims.length;if(a>0&&e.length>a&&e[a].dims.length>0)e[a].getFloat32Array().forEach(m=>i.push(m));else if(t.coordinateTransformMode==="tf_crop_and_resize")throw new Error("Resize requires RoI input to be specified when coordinateTransformMode is tfCropAndResize");if(d>0&&e.length>d&&e[d].dims.length===1&&e[d].dims[0]>0){if(e[d].getFloat32Array().forEach(m=>n.push(m)),n.length!==0&&n.length!==p&&r>=18&&n.length!==t.axes.length)throw new Error("Resize requires scales input size to be same as input rank or axes size for opset 18 and up");Ph(n,t),t.axes.length>0&&zh(n,t.axes,p).forEach((m,u)=>n[u]=m)}if(l>0&&e.length>l&&e[l].dims.length===1&&e[l].dims[0]>0&&(e[l].getBigInt64Array().forEach(m=>o.push(Number(m))),o.length!==0&&o.length!==p&&r>=18&&o.length!==t.axes.length))throw new Error("Resize requires sizes input size to be same as input rank or axes size for opset 18 and up");if(t.axes.length>0){if(n.length!==0&&n.length!==t.axes.length)throw new Error('Resize requires "scales" input size to be of axes rank when axes attributes is specified');if(o.length!==0&&o.length!==t.axes.length)throw new Error('Resize requires "sizes" input size to be of rank axes rank when axes attributes is specified')}if(typeof n<"u"&&typeof o<"u"&&n.length>0&&o.length>p)throw new Error("Resize requires only of scales or sizes to be specified")},kl=(e,t,r,n)=>`
  // The whole part and the fractional part are calculated separately due to inaccuracy of floating
  // point division. As an example, f32(21) / f32(7) may evaluate to 2.99... instead of 3, causing an
  // offset-by-one error later in floor().
  let big = (${e}) * (${t});
  let whole = ${n}(big / (${r}));
  let fract = ${n}(big % (${r})) / ${n}(${r});
  return whole + fract;
`,Dh=(e,t)=>`fn getOriginalCoordinateFromResizedCoordinate(xResized: u32, xScale: f32, lengthResized: u32,
     lengthOriginal: u32, roiStart: f32, roiEnd: f32) -> ${t} { `+(()=>{switch(e){case"asymmetric":return`
          if (xScale < 1.0 || floor(xScale) != xScale) {
            return ${t}(xResized) / ${t}(xScale);
          } else {
            ${kl("xResized","lengthOriginal","lengthResized",t)}
          }
        `;case"pytorch_half_pixel":return`if (lengthResized > 1) {
                    return (${t}(xResized) + 0.5) / ${t}(xScale) - 0.5;
                  } else {
                    return 0.0;
                  }`;case"tf_half_pixel_for_nn":return`return (${t}(xResized) + 0.5) / ${t}(xScale);`;case"align_corners":return`if (lengthResized == 1) {
                    return 0.0;
                  } else {
                    ${kl("xResized","lengthOriginal - 1","lengthResized - 1",t)}
                  }`;case"tf_crop_and_resize":return`if (lengthResized > 1) {
                    return ${t}(roiStart) * ${t}(lengthOriginal - 1) +
                        (${t}(xResized) * ${t}(roiEnd - roiStart) * ${t}(lengthOriginal - 1)) /
                        ${t}(lengthResized - 1);
                  } else {
                    return 0.5 * ${t}(roiStart + roiEnd) * ${t}(lengthOriginal - 1);
                  }`;case"half_pixel_symmetric":return`const outputWidth = ${t}xScale * ${t}(lengthResized);
                  const adjustment = ${t}(lengthResized) / outputWidth;
                  const center = ${t}(lengthOriginal) / 2;
                  const offset = center * (1 - adjustment);
                  return offset + ((${t}(xResized) + 0.5) / ${t}(xScale)) - 0.5;`;case"half_pixel":return`return ((${t}(xResized) + 0.5) / ${t}(xScale)) - 0.5;`;default:throw new Error(`Coordinate transform mode ${e} is not supported`)}})()+"}",Bh=(e,t,r)=>`fn getNearestPixelFromOriginal(xOriginal: ${r}, isDownSample: bool) -> ${r} {`+(()=>{switch(e){case"round_prefer_ceil":return"if (fract(xOriginal) == 0.5) {             return ceil(xOriginal);           } else {             return round(xOriginal);           }";case"floor":return"return floor(xOriginal);";case"ceil":return"return ceil(xOriginal);";case"round_prefer_floor":return"if (fract(xOriginal) == 0.5) {                     return floor(xOriginal);                   } else {                     return round(xOriginal);                   }";case"simple":default:if(t<11)return"if (isDownSample)                     {                       return ceil(xOriginal);                     } else {                       return xOriginal;                     }";throw new Error(`Nearest mode ${e} is not supported`)}})()+"}",Mh=(e,t,r)=>{let n=new Array(r).fill(0).concat(new Array(r).fill(1)),o=e.length===0?n:e.slice();return t.length>0?(t.forEach((i,a)=>{n[i]=o[a],n[a+r]=o[t.length+a]}),n):o},Rh=(e,t,r,n)=>{let o=[];if(r.length>0)if(n.length>0){if(e.forEach(i=>o.push(i)),Math.max(...n)>e.length)throw new Error("axes is out of bound");n.forEach((i,a)=>o[i]=r[a])}else r.forEach(i=>o.push(i));else{if(t.length===0)throw new Error("Resize requires either scales or sizes.");o=e.map((i,a)=>Math.round(i*t[a]))}return o},Uh=(e,t,r)=>{let n=(()=>{switch(r.keepAspectRatioPolicy){case"not_larger":return r.axes.length>0?Math.min(...r.axes.map(i=>t[i]),Number.MAX_VALUE):Math.min(...t,Number.MAX_VALUE);case"not_smaller":return r.axes.length>0?Math.max(...r.axes.map(i=>t[i]),Number.MIN_VALUE):Math.max(...t,Number.MIN_VALUE);default:throw new Error(`Keep aspect ratio policy ${r.keepAspectRatioPolicy} is not supported`)}})();t.fill(1,0,t.length);let o=e.slice();return r.axes.length>0?(r.axes.forEach(i=>t[i]=n),r.axes.forEach(i=>o[i]=Math.round(e[i]*t[i]))):(t.fill(n,0,t.length),o.forEach((i,a)=>o[a]=Math.round(i*t[a]))),o},Nh=(e,t,r,n,o)=>`
    fn calculateOriginalIndicesFromOutputIndices(output_indices: ${e.type.indices}) -> array<${e.type.value}, ${r.length}> {
      var original_indices: array<${e.type.value}, ${r.length}>;
      for (var i:u32 = 0; i < ${r.length}; i++) {
        var output_index = ${e.indicesGet("output_indices","i")};
        var scale = ${q("uniforms.scales","i",n)};
        var roi_low = ${q("uniforms.roi","i",o)};
        var roi_hi = ${q("uniforms.roi",`i + ${t.length}`,o)};
        if (scale == 1.0) {
          original_indices[i] = ${e.type.value}(output_index);
        } else {
          var input_shape_i = ${q("uniforms.input_shape","i",t.length)};
          var output_shape_i = ${q("uniforms.output_shape","i",r.length)};
          original_indices[i] = getOriginalCoordinateFromResizedCoordinate(output_index, scale, output_shape_i,
                                                                           input_shape_i, roi_low, roi_hi);
        }
      }
      return original_indices;
    }`,Vh=(e,t,r,n,o,i,a)=>`
    fn calculateInputIndicesFromOutputIndices(output_indices: ${t.type.indices}) -> ${e.type.indices} {
      var input_indices: ${e.type.indices};
      for (var i:u32 = 0; i < ${n.length}; i++) {
        var output_index = ${t.indicesGet("output_indices","i")};
        var input_index: u32;
        var scale = ${q("uniforms.scales","i",o)};
        if (scale == 1.0) {
          input_index = output_index;
        } else {
          var roi_low = ${q("uniforms.roi","i",i)};
          var roi_hi = ${q("uniforms.roi",`i + ${r.length}`,i)};
          var input_shape_i = ${q("uniforms.input_shape","i",r.length)};
          var output_shape_i = ${q("uniforms.output_shape","i",n.length)};
          var original_idx = getOriginalCoordinateFromResizedCoordinate(output_index, scale, output_shape_i,
                                                                        input_shape_i, roi_low, roi_hi);
          if (!${a} || (original_idx >= 0 && original_idx < ${t.type.value}(input_shape_i))) {
            if (original_idx < 0) {
              input_index = 0;
            } else if (original_idx > ${t.type.value}(input_shape_i - 1)) {
              input_index = input_shape_i - 1;
            } else {
              input_index = u32(getNearestPixelFromOriginal(original_idx, scale < 1));
            }
          } else {
            input_index = u32(original_idx);
          }
        }
        ${e.indicesSet("input_indices","i","input_index")}
      }
      return input_indices;
    }`,Wh=(e,t)=>`
    fn checkInputIndices(input_indices: ${e.type.indices}) -> bool {
      for (var i:u32 = 0; i < ${t.length}; i++) {
        var input_index = ${e.indicesGet("input_indices","i")};
        if (input_index < 0 || input_index >= ${q("uniforms.input_shape","i",t.length)}) {
          return false;
        }
      }
      return true;
    }`,El=(e,t,r,n)=>e.rank>n?`
    ${e.indicesSet("input_indices",t,"channel")};
    ${e.indicesSet("input_indices",r,"batch")};
`:"",Lh=(e,t,r,n,o)=>{let[a,d,l,p]=r.length===2?[-1,0,1,-1]:[0,2,3,1],m=e.type.value;return`
    fn getInputValue(batch: u32, channel: u32, row: u32, col: u32) -> ${m} {
      var input_indices: ${e.type.indices};
      ${e.indicesSet("input_indices",d,`max(0, min(row, ${r[d]} - 1))`)};
      ${e.indicesSet("input_indices",l,`max(0, min(col, ${r[l]} - 1))`)};
      ${El(e,p,a,2)}
      return ${e.getByIndices("input_indices")};
    }

    fn bilinearInterpolation(output_indices: ${t.type.indices}) -> ${m} {
      var originalIndices = calculateOriginalIndicesFromOutputIndices(output_indices);
      var row:${m} = originalIndices[${d}];
      var col:${m} = originalIndices[${l}];
      ${n?`if (row < 0 || row > (${r[d]} - 1) || col < 0 || col > (${r[l]} - 1)) {
        return ${o};
      }`:""};
      row = max(0, min(row, ${r[d]} - 1));
      col = max(0, min(col, ${r[l]} - 1));
      var row1: u32 = u32(row);
      var col1: u32 = u32(col);
      var row2: u32 = u32(row + 1);
      var col2: u32 = u32(col + 1);
      var channel: u32 = ${r.length>2?`u32(originalIndices[${p}])`:"0"};
      var batch: u32 =  ${r.length>2?`u32(originalIndices[${a}])`:"0"};
      var x11: ${m} = getInputValue(batch, channel, row1, col1);
      var x12: ${m} = getInputValue(batch, channel, row1, col2);
      var x21: ${m} = getInputValue(batch, channel, row2, col1);
      var x22: ${m} = getInputValue(batch, channel, row2, col2);
      var dx1: ${m} = abs(row - ${m}(row1));
      var dx2: ${m} = abs(${m}(row2) - row);
      var dy1: ${m} = abs(col - ${m}(col1));
      var dy2: ${m} = abs(${m}(col2) - col);
      if (row1 == row2) {
        dx1 = 0.5;
        dx2 = 0.5;
      }
      if (col1 == col2) {
        dy1 = 0.5;
        dy2 = 0.5;
      }
      return (x11 * dx2 * dy2 + x12 * dx2 * dy1 + x21 * dx1 * dy2 + x22 * dx1 * dy1);
    }`},Gh=(e,t,r,n,o,i,a,d,l,p)=>{let m=r.length===2,u=!0,[h,_]=m?[0,1]:u?[2,3]:[1,2],y=e.type.value,g=x=>{let $=x===h?"row":"col";return`
      fn ${$}CubicInterpolation(input_indices: ${e.type.indices}, output_indices: ${t.type.indices}) -> ${y} {
        var output_index = ${t.indicesGet("output_indices",x)};
        var originalIdx: ${y} = getOriginalCoordinateFromResizedCoordinate(output_index, ${o[x]},
        ${n[x]}, ${r[x]}, ${i[x]}, ${i[x]} + ${r.length});
        var fractOriginalIdx: ${y} = originalIdx - floor(originalIdx);
        var coefs = getCubicInterpolationCoefs(fractOriginalIdx);

        if (${d} && (originalIdx < 0 || originalIdx > (${r[x]} - 1))) {
          return ${l};
        }
        var data: array<${y}, 4> = array<${y}, 4>(0.0, 0.0, 0.0, 0.0);
        for (var i: i32 = -1; i < 3; i++) {
          var ${$}: ${y} = originalIdx + ${y}(i);
          if (${$} < 0 || ${$} >= ${r[x]}) {
            ${(()=>p?`coefs[i + 1] = 0.0;
                        continue;`:d?`return ${l};`:`${$} = max(0, min(${$}, ${r[x]} - 1));`)()};
          }
        var input_indices_copy: ${e.type.indices} = input_indices;
          ${e.indicesSet("input_indices_copy",x,`u32(${$})`)};
          data[i + 1] = ${x===h?e.getByIndices("input_indices_copy"):"rowCubicInterpolation(input_indices_copy, output_indices)"};
        }
        return cubicInterpolation1D(data, coefs);
      }`};return`
    ${g(h)};
    ${g(_)};
  fn getCubicInterpolationCoefs(s: ${y}) -> array<${y}, 4> {
    var absS = abs(s);
    var coeffs: array<${y}, 4> = array<${y}, 4>(0.0, 0.0, 0.0, 0.0);
    var oneMinusAbsS: ${y} = 1.0 - absS;
    var twoMinusAbsS: ${y} = 2.0 - absS;
    var onePlusAbsS: ${y} = 1.0 + absS;
    coeffs[0] = ((${a} * onePlusAbsS - 5 * ${a}) * onePlusAbsS + 8 * ${a}) * onePlusAbsS - 4 * ${a};
    coeffs[1] = ((${a} + 2) * absS - (${a} + 3)) * absS * absS + 1;
    coeffs[2] = ((${a} + 2) * oneMinusAbsS - (${a} + 3)) * oneMinusAbsS * oneMinusAbsS + 1;
    coeffs[3] = ((${a} * twoMinusAbsS - 5 * ${a}) * twoMinusAbsS + 8 * ${a}) * twoMinusAbsS - 4 * ${a};
    return coeffs;
  }

  fn cubicInterpolation1D(x: array<${y}, 4>, coefs: array<${y}, 4>) -> ${y} {
    var coefsSum: ${y} = coefs[0] + coefs[1] + coefs[2] + coefs[3];
    return (x[0] * coefs[0] + x[1] * coefs[1]+ x[2] * coefs[2]+ x[3] * coefs[3]) / coefsSum;
  }

  fn bicubicInterpolation(output_indices: ${t.type.indices}) -> ${y} {
    var input_indices: ${e.type.indices} = output_indices;
    return colCubicInterpolation(input_indices, output_indices);
  }
    `},Hh=(e,t,r,n,o)=>{let[a,d,l,p,m]=r.length===3?[-1,0,1,2,-1]:[0,2,3,4,1],u=e.type.value;return`
    fn getInputValue(batch: u32, channel: u32, depth:u32, height: u32, width: u32) -> ${u} {
      var input_indices: ${e.type.indices};
      ${e.indicesSet("input_indices",d,`max(0, min(depth, ${r[d]} - 1))`)};
      ${e.indicesSet("input_indices",l,`max(0, min(height, ${r[l]} - 1))`)};
      ${e.indicesSet("input_indices",p,`max(0, min(width, ${r[p]} - 1))`)};
      ${El(e,m,a,3)}
      return ${e.getByIndices("input_indices")};
    }

    fn trilinearInterpolation(output_indices: ${t.type.indices}) -> ${u} {
      var originalIndices = calculateOriginalIndicesFromOutputIndices(output_indices);
      var depth:${u} = originalIndices[${d}];
      var height:${u} = originalIndices[${l}];
      var width:${u} = originalIndices[${p}];
      ${n?`if (depth < 0 || depth > (${r[d]} - 1) || height < 0 || height > (${r[l]} - 1) || width < 0 || (width > ${r[p]} - 1)) {
      return ${o};
        }`:""};

    depth = max(0, min(depth, ${r[d]} - 1));
      height = max(0, min(height, ${r[l]} - 1));
      width = max(0, min(width, ${r[p]} - 1));
      var depth1: u32 = u32(depth);
      var height1: u32 = u32(height);
      var width1: u32 = u32(width);
      var depth2: u32 = u32(depth + 1);
      var height2: u32 = u32(height + 1);
      var width2: u32 = u32(width + 1);
      var channel: u32 = ${r.length>3?`u32(originalIndices[${m}])`:"0"};
      var batch: u32 =  ${r.length>3?`u32(originalIndices[${a}])`:"0"};

      var x111: ${u} = getInputValue(batch, channel, depth1, height1, width1);
      var x112: ${u} = getInputValue(batch, channel, depth1, height1, width2);
      var x121: ${u} = getInputValue(batch, channel, depth1, height2, width1);
      var x122: ${u} = getInputValue(batch, channel, depth1, height2, width2);
      var x211: ${u} = getInputValue(batch, channel, depth2, height1, width1);
      var x212: ${u} = getInputValue(batch, channel, depth2, height1, width2);
      var x221: ${u} = getInputValue(batch, channel, depth2, height2, width1);
      var x222: ${u} = getInputValue(batch, channel, depth2, height2, width2);
      var dx1: ${u} = abs(depth - ${u}(depth1));
      var dx2: ${u} = abs(${u}(depth2) - depth);
      var dy1: ${u} = abs(height - ${u}(height1));
      var dy2: ${u} = abs(${u}(height2) - height);
      var dz1: ${u} = abs(width - ${u}(width1));
      var dz2: ${u} = abs(${u}(width2) - width);
      if (depth1 == depth2) {
        dx1 = 0.5;
        dx2 = 0.5;
      }
      if (height1 == height2) {
        dy1 = 0.5;
        dy2 = 0.5;
      }
      if (width1 == width2) {
        dz1 = 0.5;
        dz2 = 0.5;
      }
      return (x111 * dx2 * dy2 * dz2 + x112 * dx2 * dy2 * dz1 + x121 * dx2 * dy1 *dz2 + x122 * dx2 * dy1 * dz1 +
              x211 * dx1 * dy2 * dz2 + x212 * dx1 * dy2 * dz1 + x221 * dx1 * dy1 *dz2 + x222 * dx1 * dy1 * dz1);
    }`},Fh=(e,t,r,n,o,i)=>{let a=e.dims,d=Mh(i,t.axes,a.length),l=Rh(a,n,o,t.axes),p=n.slice();n.length===0&&(p=a.map((v,S)=>v===0?1:l[S]/v),t.keepAspectRatioPolicy!=="stretch"&&(l=Uh(a,p,t)));let m=M("output",e.dataType,l.length),u=E("input",e.dataType,a.length),h=k.size(l),_=a.length===l.length&&a.every((v,S)=>v===l[S]),y=t.coordinateTransformMode==="tf_crop_and_resize",g=t.extrapolationValue,x=u.type.value,$=v=>`
      ${_?"":`
      ${Dh(t.coordinateTransformMode,x)};
      ${(()=>{switch(t.mode){case"nearest":return`
              ${Wh(u,a)};
              ${Bh(t.nearestMode,r,x)};
              ${Vh(u,m,a,l,p.length,d.length,y)};
              `;case"linear":return`
              ${Nh(m,a,l,p.length,d.length)};
              ${(()=>{if(a.length===2||a.length===4)return`${Lh(u,m,a,y,g)}`;if(a.length===3||a.length===5)return`${Hh(u,m,a,y,g)}`;throw Error("Linear mode only supports input dims 2, 3, 4 and 5 are supported in linear mode.")})()};
            `;case"cubic":return`
            ${(()=>{if(a.length===2||a.length===4)return`${Gh(u,m,a,l,p,d,t.cubicCoeffA,y,t.extrapolationValue,t.excludeOutside)}`;throw Error("Cubic mode only supports input dims 2 and 4 are supported in linear mode.")})()};
            `;default:throw Error("Invalid resize mode")}})()};
      `}
      ${v.registerUniform("output_size","u32").registerUniform("scales","f32",p.length).registerUniform("roi","f32",d.length).declareVariables(u,m)}
      ${v.mainStart()}
        ${v.guardAgainstOutOfBoundsWorkgroupSizes("uniforms.output_size")}
        ${_?"output[global_idx] = input[global_idx];":`
        let output_indices = ${m.offsetToIndices("global_idx")};
        var input_indices: ${u.type.indices};
        ${(()=>{switch(t.mode){case"nearest":return`input_indices = calculateInputIndicesFromOutputIndices(output_indices);
                if (checkInputIndices(input_indices)) {
                  output[global_idx] = ${u.getByIndices("input_indices")};
                } else {
                  output[global_idx] = ${t.extrapolationValue};
                }`;case"linear":return`output[global_idx] = ${a.length===2||a.length===4?"bilinearInterpolation":"trilinearInterpolation"}(output_indices);`;case"cubic":return"output[global_idx] = bicubicInterpolation(output_indices);";default:throw Error(`Unsupported resize mode: ${t.mode}`)}})()};
`}
      }`;return{name:"Resize",shaderCache:{hint:`${t.cacheKey}|${r}|${p.length>0?t.mode==="cubic"?p:p.length:""}|${o.length>0?o:""}|${d.length>0?d:""}|${_}|${t.mode==="nearest"?a.length:a}`,inputDependencies:["rank"]},getShaderSource:$,getRunData:()=>({outputs:[{dims:l,dataType:e.dataType}],dispatchGroup:{x:Math.ceil(h/64)},programUniforms:[{type:12,data:h},{type:1,data:p},{type:1,data:d},...N(a,l)]})}},qh=e=>{let t=e.customDataBuffer;return new Uint32Array(t,t.byteOffset,1)[0]},Pl=(e,t)=>{let r=[],n=[],o=[],i=qh(e);if(t.antialias!==0)throw Error("Only default value (0) for Antialias attribute is supported");Oh(e.inputs,t,i,r,n,o),e.compute(Fh(e.inputs[0],t,i,r,n,o),{inputs:[0]})},zl=e=>{let t=e.antialias,r=e.axes,n=e.coordinateTransformMode,o=e.cubicCoeffA,i=e.excludeOutside!==0,a=e.extrapolationValue,d=e.keepAspectRatioPolicy,l=e.mode,p=e.nearestMode===""?"simple":e.nearestMode;return ee({antialias:t,axes:r,coordinateTransformMode:n,cubicCoeffA:o,excludeOutside:i,extrapolationValue:a,keepAspectRatioPolicy:d,mode:l,nearestMode:p})}});var Kh,jh,Dl,Bl=U(()=>{"use strict";J();ne();xe();ae();Kh=(e,t)=>{let[r,n,o,i]=e,{numHeads:a,rotaryEmbeddingDim:d}=t;if(r.dims.length!==3&&r.dims.length!==4)throw new Error(`Input 'x' is expected to have 3 or 4 dimensions, got ${r.dims.length}`);if(!k.areEqual(n.dims,[])&&!k.areEqual(n.dims,[1])&&n.dims.length!==2)throw new Error(`Input 'position_ids' is expected to have 0, 1, or 2 dimensions, got ${n.dims.length}`);if(o.dims.length!==2)throw new Error(`Input 'cos_cache' is expected to have 2 dimensions, got ${o.dims.length}`);if(i.dims.length!==2)throw new Error(`Input 'sin_cache' is expected to have 2 dimensions, got ${i.dims.length}`);if(!k.areEqual(o.dims,i.dims))throw new Error("Inputs 'cos_cache' and 'sin_cache' are expected to have the same shape");if(d>0&&a===0)throw new Error("num_heads must be provided if rotary_embedding_dim is specified");let l=r.dims[0],p=r.dims[r.dims.length-2],m=o.dims[0],u=k.sizeFromDimension(r.dims,1)/p,h=d===0?o.dims[1]*2:u/a;if(d>h)throw new Error("rotary_embedding_dim must be less than or equal to head_size");if(n.dims.length===2){if(l!==n.dims[0])throw new Error(`Input 'position_ids' dimension 0 should be of size batch_size, got ${n.dims[0]}`);if(p!==n.dims[1])throw new Error(`Input 'position_ids' dimension 1 should be of size sequence_length, got ${n.dims[1]}`)}if(h/2!==o.dims[1]&&d/2!==o.dims[1])throw new Error(`Input 'cos_cache' dimension 1 should be same as head_size / 2 or rotary_embedding_dim / 2, got ${o.dims[1]}`);if(p>m)throw new Error("Updating cos_cache and sin_cache in RotaryEmbedding is not currently supported")},jh=(e,t)=>{let{interleaved:r,numHeads:n,rotaryEmbeddingDim:o,scale:i}=t,a=e[0].dims[0],d=k.sizeFromDimension(e[0].dims,1),l=e[0].dims[e[0].dims.length-2],p=d/l,m=e[2].dims[1],u=o===0?m*2:p/n,h=new Array(a,l,p/u,u-m),_=k.computeStrides(h),y=[{type:1,data:i},{type:12,data:h},{type:12,data:_},...e[0].dims.length===3?new Array({type:12,data:[d,p,u,1]}):[],...e[0].dims.length===4?new Array({type:12,data:[d,u,l*u,1]}):[],...N(e[0].dims,e[1].dims,e[2].dims,e[3].dims,e[0].dims)],g=x=>{let $=E("input",e[0].dataType,e[0].dims.length),v=E("position_ids",e[1].dataType,e[1].dims.length),S=E("cos_cache",e[2].dataType,e[2].dims.length),T=E("sin_cache",e[3].dataType,e[3].dims.length),A=M("output",e[0].dataType,e[0].dims.length);return x.registerUniforms([{name:"scale",type:"f32"},{name:"global_shape",type:"u32",length:h.length},{name:"global_strides",type:"u32",length:_.length},{name:"input_output_strides",type:"u32",length:_.length}]),`
        ${x.declareVariables($,v,S,T,A)}

        ${x.mainStart(Et)}
          let half_rotary_emb_dim = uniforms.${S.name}_shape[1];
          let bsnh = global_idx / uniforms.global_strides % uniforms.global_shape;
          let size = uniforms.global_shape[0] * uniforms.global_strides[0];
          ${x.guardAgainstOutOfBoundsWorkgroupSizes("size")}

          if (bsnh[3] < half_rotary_emb_dim) {
            let position_ids_idx =
                ${v.broadcastedIndicesToOffset("bsnh.xy",M("",v.type.tensor,2))};
            let position_id =
                u32(${v.getByOffset("position_ids_idx")}) + select(0, bsnh[1], position_ids_idx == 0);
            let i = dot(bsnh, uniforms.input_output_strides) + select(0, bsnh[3], ${r});
            let j = i + select(half_rotary_emb_dim, 1, ${r});
            let re = ${$.getByOffset("i")} * ${S.get("position_id","bsnh[3]")} -
                ${$.getByOffset("j")} * ${T.get("position_id","bsnh[3]")};
            ${A.setByOffset("i","re")}
            let im = ${$.getByOffset("i")} * ${T.get("position_id","bsnh[3]")} +
                ${$.getByOffset("j")} * ${S.get("position_id","bsnh[3]")};
            ${A.setByOffset("j","im")}
          } else {
            let k = dot(bsnh, uniforms.input_output_strides) + half_rotary_emb_dim;
            ${A.setByOffset("k",$.getByOffset("k"))}
          }
        }`};return{name:"RotaryEmbedding",shaderCache:{hint:ee({interleaved:r}).cacheKey,inputDependencies:["rank","rank","rank","rank"]},getShaderSource:g,getRunData:()=>({outputs:[{dims:e[0].dims,dataType:e[0].dataType}],dispatchGroup:{x:Math.ceil(k.size(h)/Et)},programUniforms:y})}},Dl=(e,t)=>{Kh(e.inputs,t),e.compute(jh(e.inputs,t))}});var Yh,Zh,Ml,Rl=U(()=>{"use strict";J();ne();ae();Yh=e=>{if(!e||e.length<3)throw new Error("layerNorm requires at least 3 inputs.");let t=e[0],r=e[1],n=e[2];if(t.dataType!==r.dataType||t.dataType!==n.dataType)throw new Error("All inputs must have the same data type");if(t.dims.length!==3&&t.dims.length!==2)throw new Error("Input must be 2D or 3D");if(r.dims.length!==3&&r.dims.length!==2)throw new Error("Skip must be 2D or 3D");let o=t.dims[t.dims.length-1],i=t.dims[t.dims.length-2];if(r.dims[r.dims.length-1]!==o)throw new Error("Skip must have the same hidden size as input");if(r.dims[r.dims.length-2]!==i)throw new Error("Skip must have the same sequence length as input");if(n.dims.length!==1)throw new Error("Gamma must be 1D");if(n.dims[n.dims.length-1]!==o)throw new Error("Gamma must have the same hidden size as input");if(e.length>3){let a=e[3];if(a.dims.length!==1)throw new Error("Beta must be 1D");if(a.dims[a.dims.length-1]!==o)throw new Error("Beta must have the same hidden size as input")}if(e.length>4){let a=e[4];if(a.dims.length!==1)throw new Error("Bias must be 1D");if(a.dims[a.dims.length-1]!==o)throw new Error("Bias must have the same hidden size as input")}},Zh=(e,t,r,n)=>{let o=t.simplified,i=e[0].dims,a=k.size(i),d=i,l=a,p=i.slice(-1)[0],m=n?i.slice(0,-1).concat(1):[],u=!o&&e.length>3,h=e.length>4,_=n&&r>1,y=n&&r>2,g=r>3,x=64,$=me(p),v=[{type:12,data:l},{type:12,data:$},{type:12,data:p},{type:1,data:t.epsilon}],S=A=>{let C=[{name:"output_size",type:"u32"},{name:"components",type:"u32"},{name:"hidden_size",type:"u32"},{name:"epsilon",type:"f32"}],P=[E("x",e[0].dataType,e[0].dims,$),E("skip",e[1].dataType,e[1].dims,$),E("gamma",e[2].dataType,e[2].dims,$)];u&&P.push(E("beta",e[3].dataType,e[3].dims,$)),h&&P.push(E("bias",e[4].dataType,e[4].dims,$)),P.push(M("output",e[0].dataType,d,$)),_&&P.push(M("mean_output",1,m)),y&&P.push(M("inv_std_output",1,m)),g&&P.push(M("input_skip_bias_sum",e[0].dataType,d,$));let D=ye(e[0].dataType),R=ye(1,$);return`

      ${A.registerUniforms(C).declareVariables(...P)}
      var<workgroup> sum_shared : array<${R}, ${x}>;
      var<workgroup> sum_squared_shared : array<${R}, ${x}>;

      ${A.mainStart([x,1,1])}
        let ix = local_id.x;
        let iy = global_id.x / ${x};

        let hidden_size_vectorized: u32 = uniforms.hidden_size / uniforms.components;
        var stride = hidden_size_vectorized / ${x};
        let offset = ix * stride + iy * hidden_size_vectorized;
        let offset1d = stride * ix;
        if (ix == ${x-1}) {
          stride = hidden_size_vectorized - stride * ix;
        }
        for (var i: u32 = 0; i < stride; i++) {
          let skip_value = skip[offset + i];
          let bias_value = ${h?"bias[offset1d + i]":D+"(0.0)"};
          let input_value = x[offset + i];
          let value = input_value + skip_value + bias_value;
          ${g?"input_skip_bias_sum[offset + i] = value;":""}
          output[offset + i] = value;
          let f32_value = ${Pt(D,$,"value")};
          sum_shared[ix] += f32_value;
          sum_squared_shared[ix] += f32_value * f32_value;
        }
        workgroupBarrier();

        var reduce_size : u32 = ${x};
        for (var curr_size = reduce_size >> 1;  curr_size > 0; curr_size = reduce_size >> 1) {
          reduce_size = curr_size + (reduce_size & 1);
          if (ix < curr_size) {
            sum_shared[ix] += sum_shared[ix + reduce_size];
            sum_squared_shared[ix] += sum_squared_shared[ix + reduce_size];
          }
          workgroupBarrier();
        }

        let sum = sum_shared[0];
        let square_sum = sum_squared_shared[0];
        let mean = ${qe("sum",$)} / f32(uniforms.hidden_size);
        let inv_std_dev = inverseSqrt(${qe("square_sum",$)} / f32(uniforms.hidden_size) ${o?"":"- mean * mean"} + uniforms.epsilon);
        ${_?"mean_output[global_idx] = mean;":""}
        ${y?"inv_std_output[global_idx] = inv_std_dev;":""}

        for (var i: u32 = 0; i < stride; i++) {
          output[offset + i] = (output[offset + i] ${o?"":`- ${D}(mean)`}) *
            ${D}(inv_std_dev) * gamma[offset1d + i]
            ${u?"+ beta[offset1d + i]":""};
        }
      }`},T=[{dims:d,dataType:e[0].dataType}];return r>1&&T.push({dims:m,dataType:1}),r>2&&T.push({dims:m,dataType:1}),r>3&&T.push({dims:i,dataType:e[0].dataType}),{name:"SkipLayerNormalization",shaderCache:{hint:`${$};${_};${y};${g}`,inputDependencies:e.map((A,C)=>"type")},getShaderSource:S,getRunData:()=>({outputs:T,dispatchGroup:{x:Math.ceil(l/p)},programUniforms:v})}},Ml=(e,t)=>{Yh(e.inputs);let n=[0];e.outputCount>1&&n.push(-3),e.outputCount>2&&n.push(-3),e.outputCount>3&&n.push(3),e.compute(Zh(e.inputs,t,e.outputCount,!1),{outputs:n})}});var Qh,tn,Xh,Ul,Jh,eg,Nl,Vl,Wl=U(()=>{"use strict";J();ne();xe();ae();Qh=(e,t)=>{if(!e||e.length<1)throw new Error("too few inputs");if(t.axes.length!==0){if(t.axes.length!==t.starts.length||t.axes.length!==t.ends.length)throw new Error("axes, starts and ends must have the same length")}else if(t.starts.length!==t.ends.length)throw new Error("starts and ends must have the same length");e.slice(1).forEach((r,n)=>{if(e[n+1].dataType!==6&&e[n+1].dataType!==7)throw new Error(`Input ${n} must be an array of int32 or int64`)})},tn=(e,t)=>{let r=[];if(e.length>t)if(e[t].dataType===7)e[t].getBigInt64Array().forEach(n=>r.push(Number(n)));else if(e[t].dataType===6)e[t].getInt32Array().forEach(n=>r.push(Number(n)));else throw new Error(`Input ${t} must be an array of int32 or int64`);return r},Xh=(e,t)=>{if(e.length>1){let r=tn(e,1),n=tn(e,2),o=tn(e,3);return o.length===0&&(o=[...Array(e[0].dims.length).keys()]),ee({starts:r,ends:n,axes:o})}else return t},Ul=(e,t,r,n,o)=>{let i=e;return e<0&&(i+=r[n[t]]),o[t]<0?Math.max(0,Math.min(i,r[n[t]]-1)):Math.max(0,Math.min(i,r[n[t]]))},Jh=(e,t,r)=>`fn calculateInputIndices(output_indices: ${t.type.indices}) -> ${e.type.indices} {
          var input_indices: ${e.type.indices};
          var carry = 0u;
          for (var i = ${r.length}; i >= 0; i--) {
            let input_shape_i = ${q("uniforms.input_shape","i",r.length)};
            let steps_i = ${q("uniforms.steps","i",r.length)};
            let signs_i = ${q("uniforms.signs","i",r.length)};
            let starts_i = ${q("uniforms.starts","i",r.length)};
            var output_index = ${t.indicesGet("output_indices","i")};
            var input_index = output_index * steps_i + starts_i + carry;
            carry = input_index / input_shape_i;
            input_index = input_index % input_shape_i;
            if (signs_i < 0) {
              input_index = input_shape_i - input_index - 1u + starts_i;
            }
            ${e.indicesSet("input_indices","i","input_index")};
          }
          return input_indices;
      }`,eg=(e,t)=>{let r=e[0].dims,n=k.size(r),o=t.axes.length>0?k.normalizeAxes(t.axes,r.length):[...Array(r.length).keys()],i=tn(e,4);i.forEach($=>$!==0||(()=>{throw new Error("step cannot be 0")})),i.length===0&&(i=Array(o.length).fill(1));let a=t.starts.map(($,v)=>Ul($,v,r,o,i)),d=t.ends.map(($,v)=>Ul($,v,r,o,i));if(o.length!==a.length||o.length!==d.length)throw new Error("start, ends and axes should have the same number of elements");if(o.length!==r.length)for(let $=0;$<r.length;++$)o.includes($)||(a.splice($,0,0),d.splice($,0,r[$]),i.splice($,0,1));let l=i.map($=>Math.sign($));i.forEach(($,v,S)=>{if($<0){let T=(d[v]-a[v])/$,A=a[v],C=A+T*i[v];a[v]=C,d[v]=A,S[v]=-$}});let p=r.slice(0);o.forEach(($,v)=>{p[$]=Math.ceil((d[$]-a[$])/i[$])});let m={dims:p,dataType:e[0].dataType},u=M("output",e[0].dataType,p.length),h=E("input",e[0].dataType,e[0].dims.length),_=k.size(p),y=[{name:"outputSize",type:"u32"},{name:"starts",type:"u32",length:a.length},{name:"signs",type:"i32",length:l.length},{name:"steps",type:"u32",length:i.length}],g=[{type:12,data:_},{type:12,data:a},{type:6,data:l},{type:12,data:i},...N(e[0].dims,p)],x=$=>`
      ${$.registerUniforms(y).declareVariables(h,u)}
        ${Jh(h,u,r)}
        ${$.mainStart()}
          ${$.guardAgainstOutOfBoundsWorkgroupSizes("uniforms.outputSize")}
          let output_indices = ${u.offsetToIndices("global_idx")};
          let input_indices = calculateInputIndices(output_indices);
          ${u.setByOffset("global_idx",h.getByIndices("input_indices"))}
      }`;return{name:"Slice",shaderCache:{hint:`${l.length}_${a.length}_${i.length}`,inputDependencies:["rank"]},getShaderSource:x,getRunData:()=>({outputs:[m],dispatchGroup:{x:Math.ceil(n/64)},programUniforms:g})}},Nl=(e,t)=>{Qh(e.inputs,t);let r=Xh(e.inputs,t);e.compute(eg(e.inputs,r),{inputs:[0]})},Vl=e=>{let t=e.starts,r=e.ends,n=e.axes;return ee({starts:t,ends:r,axes:n})}});var tg,rg,Ll,Gl,Hl=U(()=>{"use strict";J();ne();xe();dt();ae();tg=e=>{if(!e||e.length!==1)throw new Error("Softmax op requires 1 input.")},rg=(e,t)=>{let r=e.inputs[0],n=r.dims,o=k.size(n),i=n.length,a=k.normalizeAxis(t.axis,i),d=a<n.length-1,l,p=[];d?(p=Array.from({length:i},(P,D)=>D),p[a]=i-1,p[i-1]=a,l=e.compute(Pe(r,p),{inputs:[r],outputs:[-1]})[0]):l=r;let m=l.dims,u=m[i-1],h=o/u,_=me(u),y=u/_,g=64;h===1&&(g=256);let x=(P,D)=>D===4?`max(max(${P}.x, ${P}.y), max(${P}.z, ${P}.w))`:D===2?`max(${P}.x, ${P}.y)`:D===3?`max(max(${P}.x, ${P}.y), ${P}.z)`:P,$=E("x",l.dataType,l.dims,_),v=M("result",l.dataType,l.dims,_),S=$.type.value,T=ye(l.dataType)==="f32"?`var threadMax = ${S}(-3.402823e+38f);`:`var threadMax = ${S}(-65504.0h);`,A=P=>`
      var<workgroup> rowMaxShared : ${S};
      var<workgroup> rowSumShared : ${S};
      var<workgroup> threadShared : array<${S}, ${g}>;

      fn getValue(row: i32, col: i32, row_stride: i32) -> ${S} {
        let index = row * row_stride + col;
        return x[index];
      }

      fn setValue(row: i32, col: i32, row_stride: i32, value: ${S}) {
        let index = row * row_stride + col;
        result[index] = value;
      }
      ${P.registerUniform("packedCols","i32").declareVariables($,v)}
      ${P.mainStart(g)}
        let gindex = i32(global_idx);
        let lindex = i32(local_idx);
        const wg = ${g};
        let row = gindex / wg;
        let cols = uniforms.packedCols;
        let row_stride : i32 = uniforms.packedCols;

        // find the rows max
        ${T}
        for (var col = lindex; col < cols; col += wg) {
          let value = getValue(row, col, row_stride);
          threadMax = max(threadMax, value);
        }
        if (lindex < cols) {
          threadShared[lindex] = threadMax;
        }
        workgroupBarrier();

        var reduceSize = min(cols, wg);
        for (var currSize = reduceSize >> 1;  currSize > 0; currSize = reduceSize >> 1) {
          reduceSize = currSize + (reduceSize & 1);
          if (lindex < currSize) {
            threadShared[lindex] = max(threadShared[lindex], threadShared[lindex + reduceSize]);
          }
          workgroupBarrier();
        }
        if (lindex == 0) {
          rowMaxShared = ${S}(${x("threadShared[0]",_)});
        }
        workgroupBarrier();

        // find the rows sum
        var threadSum = ${S}(0.0);
        for (var col = lindex; col < cols; col += wg) {
          let subExp = exp(getValue(row, col, row_stride) - rowMaxShared);
          threadSum += subExp;
        }
        threadShared[lindex] = threadSum;
        workgroupBarrier();

        for (var currSize = wg >> 1;  currSize > 0; currSize = currSize >> 1) {
          if (lindex < currSize) {
            threadShared[lindex] = threadShared[lindex] + threadShared[lindex + currSize];
          }
          workgroupBarrier();
        }
        if (lindex == 0) {
          rowSumShared = ${S}(${qe("threadShared[0]",_)});
        }
        workgroupBarrier();

        // calculate final value for each element in the row
        for (var col = lindex; col < cols; col += wg) {
          let value = exp(getValue(row, col, row_stride) - rowMaxShared) / rowSumShared;
          setValue(row, col, row_stride, value);
        }
      }`,C=e.compute({name:"Softmax",shaderCache:{hint:`${_};${g}`,inputDependencies:["type"]},getRunData:()=>({outputs:[{dims:m,dataType:l.dataType}],dispatchGroup:{x:h},programUniforms:[{type:6,data:y}]}),getShaderSource:A},{inputs:[l],outputs:[d?-1:0]})[0];d&&e.compute(Pe(C,p),{inputs:[C]})},Ll=(e,t)=>{tg(e.inputs),rg(e,t)},Gl=e=>ee({axis:e.axis})});var Fl,ng,og,ig,ql,Kl=U(()=>{"use strict";J();ne();ae();Fl=e=>Array.from(e.getBigInt64Array(),Number),ng=e=>{if(!e||e.length!==2)throw new Error("Tile requires 2 inputs.");if(e[0].dataType!==1&&e[0].dataType!==10&&e[0].dataType!==6&&e[0].dataType!==12)throw new Error("Tile only support float, float16, int32, and uint32 data types");if(e[1].dataType!==7)throw new Error("Tile `repeats` input should be of int64 data type");if(e[1].dims.length!==1)throw new Error("Tile `repeats` input should be 1-D");if(Fl(e[1]).length!==e[0].dims.length)throw new Error("Tile `repeats` input should have same number of elements as rank of input data tensor")},og=(e,t)=>{let r=[];for(let n=0;n<e.length;++n)r.push(e[n]*t[n]);return r},ig=(e,t)=>{let r=e[0].dims,n=t??Fl(e[1]),o=og(r,n),i=k.size(o),a=e[0].dataType,d=E("input",a,r.length),l=M("output",a,o.length),p=m=>`
      const inputShape = ${d.indices(...r)};
      ${m.registerUniform("output_size","u32").declareVariables(d,l)}
      ${m.mainStart()}
      ${m.guardAgainstOutOfBoundsWorkgroupSizes("uniforms.output_size")}
      let output_indices = ${l.offsetToIndices("global_idx")};
      var input_indices: ${d.type.indices};
      for (var i = 0; i < ${r.length}; i++) {
        let input_dim_i = ${d.indicesGet("uniforms.input_shape","i")};
        let input_dim_value = ${l.indicesGet("output_indices","i")}  % input_dim_i;

        ${d.indicesSet("input_indices","i","input_dim_value")}
      }
      ${l.setByOffset("global_idx",d.getByIndices("input_indices"))}
    }`;return{name:"Tile",shaderCache:{hint:`${n}`,inputDependencies:["rank"]},getRunData:()=>({outputs:[{dims:o,dataType:e[0].dataType}],dispatchGroup:{x:Math.ceil(i/64)},programUniforms:[{type:12,data:i},...N(e[0].dims,o)]}),getShaderSource:p}},ql=e=>{ng(e.inputs),e.compute(ig(e.inputs),{inputs:[0]})}});var ag,sg,jl,Yl=U(()=>{"use strict";J();ne();ae();ag=(e,t,r,n,o)=>{let i=M("output_data",o,r.length,4),a=E("a_data",t[1].dataType,t[1].dims.length,4),d=E("b_data",t[2].dataType,t[2].dims.length,4),l=E("c_data",t[0].dataType,t[0].dims.length,4),p,m=(u,h,_)=>`select(${h}, ${u}, ${_})`;if(!n)p=i.setByOffset("global_idx",m(a.getByOffset("global_idx"),d.getByOffset("global_idx"),l.getByOffset("global_idx")));else{let u=(h,_,y="")=>{let g=`a_data[index_a${_}][component_a${_}]`,x=`b_data[index_b${_}][component_b${_}]`,$=`bool(c_data[index_c${_}] & (0xffu << (component_c${_} * 8)))`;return`
            let output_indices${_} = ${i.offsetToIndices(`global_idx * 4u + ${_}u`)};
            let offset_a${_} = ${a.broadcastedIndicesToOffset(`output_indices${_}`,i)};
            let offset_b${_} = ${d.broadcastedIndicesToOffset(`output_indices${_}`,i)};
            let offset_c${_} = ${l.broadcastedIndicesToOffset(`output_indices${_}`,i)};
            let index_a${_} = offset_a${_} / 4u;
            let index_b${_} = offset_b${_} / 4u;
            let index_c${_} = offset_c${_} / 4u;
            let component_a${_} = offset_a${_} % 4u;
            let component_b${_} = offset_b${_} % 4u;
            let component_c${_} = offset_c${_} % 4u;
            ${h}[${_}] = ${y}(${m(g,x,$)});
          `};o===9?p=`
            var data = vec4<u32>(0);
            ${u("data",0,"u32")}
            ${u("data",1,"u32")}
            ${u("data",2,"u32")}
            ${u("data",3,"u32")}
            output_data[global_idx] = dot(vec4<u32>(0x1, 0x100, 0x10000, 0x1000000), vec4<u32>(data));`:p=`
            ${u("output_data[global_idx]",0)}
            ${u("output_data[global_idx]",1)}
            ${u("output_data[global_idx]",2)}
            ${u("output_data[global_idx]",3)}
          `}return`
        ${e.registerUniform("vec_size","u32").declareVariables(l,a,d,i)}
        ${e.mainStart()}
        ${e.guardAgainstOutOfBoundsWorkgroupSizes("uniforms.vec_size")}
        ${p}
      }`},sg=e=>{let t=e[1].dims,r=e[2].dims,n=e[0].dims,o=e[1].dataType,i=!(k.areEqual(t,r)&&k.areEqual(r,n)),a=t,d=k.size(t);if(i){let p=tt.calcShape(tt.calcShape(t,r,!1),n,!1);if(!p)throw new Error("Can't perform where op on the given tensors");a=p,d=k.size(a)}let l=Math.ceil(d/4);return{name:"Where",shaderCache:{inputDependencies:["rank","rank","rank"]},getShaderSource:p=>ag(p,e,a,i,o),getRunData:()=>({outputs:[{dims:a,dataType:o}],dispatchGroup:{x:Math.ceil(d/64/4)},programUniforms:[{type:12,data:l},...N(n,t,r,a)]})}},jl=e=>{e.compute(sg(e.inputs))}});var Zl,Ql=U(()=>{"use strict";Es();Hr();Os();Bs();wu();Pu();Du();Zu();nd();ad();dd();fd();bd();_d();$d();Td();Ad();Pd();Dd();Rd();Fd();jd();Zd();Xd();tl();xo();nl();wl();xl();Tl();Al();Lr();Ol();Bl();Rl();Wl();Hl();To();Kl();dt();qr();Yl();Zl=new Map([["Abs",[Ms]],["Acos",[Rs]],["Acosh",[Us]],["Add",[vu]],["ArgMax",[ks,lo]],["ArgMin",[As,lo]],["Asin",[Ns]],["Asinh",[Vs]],["Atan",[Ws]],["Atanh",[Ls]],["Attention",[Ps]],["AveragePool",[cl,ll]],["BatchNormalization",[zs]],["BiasAdd",[Ds]],["BiasSplitGelu",[_u]],["Cast",[Hs,Gs]],["Ceil",[qs]],["Clip",[Fs]],["Concat",[zu,Ou]],["Conv",[_o,yo]],["ConvTranspose",[rd,ed]],["Cos",[Ks]],["Cosh",[js]],["CumSum",[od,id]],["DepthToSpace",[sd,ud]],["DequantizeLinear",[vl,$l]],["Div",[$u]],["Einsum",[pd,md]],["Elu",[Ys,Qt]],["Equal",[xu]],["Erf",[Zs]],["Exp",[Qs]],["Expand",[gd]],["FastGelu",[yd]],["Floor",[Xs]],["FusedConv",[_o,yo]],["Gather",[vd,wd]],["GatherElements",[Ed,kd]],["GatherBlockQuantized",[Id,Cd]],["GatherND",[xd,Sd]],["Gelu",[Js]],["Gemm",[Od,zd]],["GlobalAveragePool",[fl,ml]],["GlobalMaxPool",[_l,yl]],["Greater",[Cu]],["GreaterOrEqual",[ku]],["GridSample",[Bd,Md]],["GroupQueryAttention",[Hd]],["HardSigmoid",[su,au]],["InstanceNormalization",[Kd]],["LayerNormalization",[Yd]],["LeakyRelu",[eu,Qt]],["Less",[Au]],["LessOrEqual",[Eu]],["Log",[gu]],["MatMul",[Qd]],["MatMulNBits",[Jd,el]],["MaxPool",[gl,bl]],["Mul",[Su]],["MultiHeadAttention",[Vd,Nd]],["Neg",[ru]],["Not",[tu]],["Pad",[rl]],["Pow",[Tu]],["QuickGelu",[bu,Qt]],["Range",[Sl]],["Reciprocal",[nu]],["ReduceMin",[$s]],["ReduceMean",[bs]],["ReduceMax",[vs]],["ReduceSum",[Ss]],["ReduceProd",[xs]],["ReduceL1",[ys]],["ReduceL2",[_s]],["ReduceLogSum",[Is]],["ReduceLogSumExp",[ws]],["ReduceSumSquare",[Ts]],["Relu",[ou]],["Resize",[Pl,zl]],["RotaryEmbedding",[Dl]],["ScatterND",[Cl,Il]],["Sigmoid",[iu]],["Sin",[uu]],["Sinh",[du]],["Slice",[Nl,Vl]],["SkipLayerNormalization",[Ml]],["Split",[Wd,Ld]],["Sqrt",[lu]],["Softmax",[Ll,Gl]],["Sub",[Iu]],["Tan",[cu]],["Tanh",[mu]],["ThresholdedRelu",[hu,Qt]],["Tile",[ql]],["Transpose",[os,is]],["Where",[jl]]])});var rn,Xl=U(()=>{"use strict";Le();et();ae();rn=class{constructor(t){this.backend=t;this.repo=new Map,this.attributesBound=!1}getArtifact(t){return this.repo.get(t)}setArtifact(t,r){this.repo.set(t,r)}run(t,r,n,o,i){Ne(t.programInfo.name);let a=this.backend.device,d=this.backend.getComputePassEncoder();this.backend.writeTimestamp(this.backend.pendingDispatchNumber*2);let l=[];for(let m of r)l.push({binding:l.length,resource:{buffer:m.buffer}});for(let m of n)l.push({binding:l.length,resource:{buffer:m.buffer}});i&&l.push({binding:l.length,resource:i});let p=a.createBindGroup({layout:t.computePipeline.getBindGroupLayout(0),entries:l,label:t.programInfo.name});if(this.backend.sessionStatus==="capturing"){let m={kernelId:this.backend.currentKernelId,computePipeline:t.computePipeline,bindGroup:p,dispatchGroup:o};this.backend.capturedCommandList.get(this.backend.currentSessionId).push(m)}d.setPipeline(t.computePipeline),d.setBindGroup(0,p),d.dispatchWorkgroups(...o),this.backend.writeTimestamp(this.backend.pendingDispatchNumber*2+1),this.backend.pendingDispatchNumber++,(this.backend.pendingDispatchNumber>=this.backend.maxDispatchNumber||this.backend.queryType==="at-passes")&&this.backend.endComputePass(),this.backend.pendingDispatchNumber>=this.backend.maxDispatchNumber&&this.backend.flush(),Be(t.programInfo.name)}dispose(){}build(t,r){Ne(t.name);let n=this.backend.device,o=[];[{feature:"shader-f16",extension:"f16"},{feature:"subgroups",extension:"subgroups"},{feature:"subgroups-f16",extension:"subgroups_f16"}].forEach(u=>{n.features.has(u.feature)&&o.push(`enable ${u.extension};`)});let a=rs(r,this.backend.device.limits),d=t.getShaderSource(a),l=`${o.join(`
`)}
${a.additionalImplementations}
${d}`,p=n.createShaderModule({code:l,label:t.name});se("verbose",()=>`[WebGPU] ${t.name} shader code: ${l}`);let m=n.createComputePipeline({compute:{module:p,entryPoint:"main"},layout:"auto",label:t.name});return Be(t.name),{programInfo:t,computePipeline:m,uniformVariablesInfo:a.variablesInfo}}normalizeDispatchGroupSize(t){let r=typeof t=="number"?t:t.x,n=typeof t=="number"?1:t.y||1,o=typeof t=="number"?1:t.z||1,i=this.backend.device.limits.maxComputeWorkgroupsPerDimension;if(r<=i&&n<=i&&o<=i)return[r,n,o];let a=r*n*o,d=Math.ceil(Math.sqrt(a));if(d>i){if(d=Math.ceil(Math.cbrt(a)),d>i)throw new Error("Total dispatch size exceeds WebGPU maximum.");return[d,d,d]}else return[d,d,1]}}});var ug,dg,Io,Co,nn,Jl=U(()=>{"use strict";Le();J();et();Xn();Xa();Ql();Xl();ug=(e,t)=>{if(t.length!==e.length)throw new Error(`inputDependencies length ${t.length} is not equal to inputTensors length ${e.length}.`);let r=[];for(let n=0;n<e.length;++n){let o=e[n].dataType;switch(t[n]){case"none":{r.push("");break}case"type":{r.push(`${o}`);break}case"rank":{let i=e[n].dims.length;r.push(`${o};${i}`);break}case"dims":{let i=e[n].dims.join(",");r.push(`${o};${i}`);break}default:throw new Error(`unsupported input dependency: ${t[n]}`)}}return r.join("|")},dg=(e,t,r)=>{let n=e.name;return e.shaderCache?.hint&&(n+="["+e.shaderCache.hint+"]"),n+=":"+r+`:${ug(t,e.shaderCache?.inputDependencies??new Array(t.length).fill("dims"))}`,n},Io=class{constructor(t){t&&(this.architecture=t.architecture,this.vendor=t.vendor)}isArchitecture(t){return this.architecture===t}isVendor(t){return this.vendor===t}},Co=class{constructor(t){this.subgroupsSupported=t.features.has("subgroups"),this.subgroupsF16Supported=t.features.has("subgroups");let r=t.limits;!this.subgroupsSupported||!r.minSubgroupSize||!r.maxSubgroupSize?this.subgroupSizeRange=void 0:this.subgroupSizeRange=[r.minSubgroupSize,r.maxSubgroupSize]}},nn=class{constructor(){this.currentSessionId=null;this.currentKernelId=null;this.commandEncoder=null;this.computePassEncoder=null;this.maxDispatchNumber=16;this.pendingDispatchNumber=0;this.pendingKernels=[];this.pendingQueries=new Map;this.sessionStatus="default";this.capturedCommandList=new Map;this.capturedPendingKernels=new Map;this.sessionExternalDataMapping=new Map}get currentKernelCustomData(){if(this.currentKernelId===null)throw new Error("currentKernelCustomData(): currentKernelId is null. (should not happen)");let t=this.kernelCustomData.get(this.currentKernelId);return t||(t={},this.kernelCustomData.set(this.currentKernelId,t)),t}async initialize(t,r){this.env=t;let n=[],o={requiredLimits:{maxComputeWorkgroupStorageSize:r.limits.maxComputeWorkgroupStorageSize,maxComputeWorkgroupsPerDimension:r.limits.maxComputeWorkgroupsPerDimension,maxStorageBufferBindingSize:r.limits.maxStorageBufferBindingSize,maxBufferSize:r.limits.maxBufferSize,maxComputeInvocationsPerWorkgroup:r.limits.maxComputeInvocationsPerWorkgroup,maxComputeWorkgroupSizeX:r.limits.maxComputeWorkgroupSizeX,maxComputeWorkgroupSizeY:r.limits.maxComputeWorkgroupSizeY,maxComputeWorkgroupSizeZ:r.limits.maxComputeWorkgroupSizeZ},requiredFeatures:n},i=a=>r.features.has(a)&&n.push(a)&&!0;i("chromium-experimental-timestamp-query-inside-passes")||i("timestamp-query"),i("shader-f16"),i("subgroups")&&i("subgroups-f16"),this.device=await r.requestDevice(o),this.deviceInfo=new Co(this.device),this.adapterInfo=new Io(r.info||await r.requestAdapterInfo()),this.gpuDataManager=Qa(this),this.programManager=new rn(this),this.kernels=new Map,this.kernelPersistentData=new Map,this.kernelCustomData=new Map,Mr(t.logLevel,!!t.debug),this.device.onuncapturederror=a=>{a.error instanceof GPUValidationError&&console.error(`An uncaught WebGPU validation error was raised: ${a.error.message}`)},Object.defineProperty(this.env.webgpu,"device",{value:this.device,writable:!1,enumerable:!0,configurable:!1}),Object.defineProperty(this.env.webgpu,"adapter",{value:r,writable:!1,enumerable:!0,configurable:!1}),this.setQueryType()}dispose(){typeof this.querySet<"u"&&this.querySet.destroy(),this.gpuDataManager.dispose()}getCommandEncoder(){return this.commandEncoder||(this.commandEncoder=this.device.createCommandEncoder()),this.commandEncoder}getComputePassEncoder(){if(!this.computePassEncoder){let t=this.getCommandEncoder(),r={};this.queryType==="at-passes"&&(r.timestampWrites={querySet:this.querySet,beginningOfPassWriteIndex:this.pendingDispatchNumber*2,endOfPassWriteIndex:this.pendingDispatchNumber*2+1}),this.computePassEncoder=t.beginComputePass(r)}return this.computePassEncoder}endComputePass(){this.computePassEncoder&&(this.computePassEncoder.end(),this.computePassEncoder=null)}flush(){if(!this.commandEncoder)return;Ne(),this.endComputePass();let t;this.queryType!=="none"&&(this.commandEncoder.resolveQuerySet(this.querySet,0,this.pendingDispatchNumber*2,this.queryResolveBuffer,0),t=this.device.createBuffer({size:this.pendingDispatchNumber*2*8,usage:GPUBufferUsage.MAP_READ|GPUBufferUsage.COPY_DST}),this.pendingQueries.set(t,this.pendingKernels),this.pendingKernels=[],this.commandEncoder.copyBufferToBuffer(this.queryResolveBuffer,0,t,0,this.pendingDispatchNumber*2*8)),this.device.queue.submit([this.commandEncoder.finish()]),this.gpuDataManager.refreshPendingBuffers(),this.commandEncoder=null,this.pendingDispatchNumber=0,this.queryType!=="none"&&t.mapAsync(GPUMapMode.READ).then(()=>{let r=new BigUint64Array(t.getMappedRange()),n=this.pendingQueries.get(t);for(let o=0;o<r.length/2;o++){let i=n[o],a=i.kernelId,d=this.kernels.get(a),l=d.kernelType,p=d.kernelName,m=i.programName,u=i.inputTensorViews,h=i.outputTensorViews,_=r[o*2],y=r[o*2+1];typeof this.queryTimeBase>"u"&&(this.queryTimeBase=_);let g=Number(_-this.queryTimeBase),x=Number(y-this.queryTimeBase);if(!Number.isSafeInteger(g)||!Number.isSafeInteger(x))throw new RangeError("incorrect timestamp range");if(this.env.webgpu.profiling?.ondata)this.env.webgpu.profiling.ondata({version:1,inputsMetadata:u.map($=>({dims:$.dims,dataType:bt($.dataType)})),outputsMetadata:h.map($=>({dims:$.dims,dataType:bt($.dataType)})),kernelId:a,kernelType:l,kernelName:p,programName:m,startTime:g,endTime:x});else{let $="";u.forEach((S,T)=>{$+=`input[${T}]: [${S.dims}] | ${bt(S.dataType)}, `});let v="";h.forEach((S,T)=>{v+=`output[${T}]: [${S.dims}] | ${bt(S.dataType)}, `}),console.log(`[profiling] kernel "${a}|${l}|${p}|${m}" ${$}${v}execution time: ${x-g} ns`)}_r("GPU",`${m}::${_}::${y}`)}t.unmap(),this.pendingQueries.delete(t)}),Be()}run(t,r,n,o,i,a){Ne(t.name);let d=[];for(let S=0;S<r.length;++S){let T=r[S].data;if(T===0)continue;let A=this.gpuDataManager.get(T);if(!A)throw new Error(`no GPU data for input: ${T}`);d.push(A)}let{outputs:l,dispatchGroup:p,programUniforms:m}=t.getRunData(r),u=n.length===0?l.map((S,T)=>T):n;if(u.length!==l.length)throw new Error(`Output size ${u.length} must be equal to ${l.length}.`);let h=[],_=[];for(let S=0;S<l.length;++S){if(!Number.isInteger(u[S])||u[S]<-3||u[S]>=a)throw new Error(`Invalid output index: ${u[S]}`);if(u[S]===-3)continue;let T=u[S]===-1,A=u[S]===-2,C=T||A?i(l[S].dataType,l[S].dims):o(u[S],l[S].dataType,l[S].dims);if(h.push(C),C.data===0)continue;let P=this.gpuDataManager.get(C.data);if(!P)throw new Error(`no GPU data for output: ${C.data}`);if(T&&this.temporaryData.push(P),A){let D=this.kernelPersistentData.get(this.currentKernelId);D||(D=[],this.kernelPersistentData.set(this.currentKernelId,D)),D.push(P)}_.push(P)}if(d.length!==r.length||_.length!==h.length){if(_.length===0)return Be(t.name),h;throw new Error(`Program ${t.name} has zero-sized tensor(s) in inputs or outputs. This is not supported now.`)}let y;if(m){let S=0,T=[];m.forEach(D=>{let R=typeof D.data=="number"?[D.data]:D.data;if(R.length===0)return;let H=D.type===10?2:4,L,re;D.type===10?(re=R.length>4?16:R.length>2?8:R.length*H,L=R.length>4?16:H*R.length):(re=R.length<=2?R.length*H:16,L=16),S=Math.ceil(S/re)*re,T.push(S);let V=D.type===10?8:4;S+=R.length>4?Math.ceil(R.length/V)*L:R.length*H});let A=16;S=Math.ceil(S/A)*A;let C=new ArrayBuffer(S);m.forEach((D,R)=>{let H=T[R],L=typeof D.data=="number"?[D.data]:D.data;if(D.type===6)new Int32Array(C,H,L.length).set(L);else if(D.type===12)new Uint32Array(C,H,L.length).set(L);else if(D.type===10)new Uint16Array(C,H,L.length).set(L);else if(D.type===1)new Float32Array(C,H,L.length).set(L);else throw new Error(`Unsupported uniform type: ${bt(D.type)}`)});let P=this.gpuDataManager.create(S,GPUBufferUsage.COPY_DST|GPUBufferUsage.UNIFORM);this.device.queue.writeBuffer(P.buffer,0,C,0,S),this.gpuDataManager.release(P.id),y={offset:0,size:S,buffer:P.buffer}}let g=this.programManager.normalizeDispatchGroupSize(p),x=g[1]===1&&g[2]===1,$=dg(t,r,x),v=this.programManager.getArtifact($);if(v||(v=this.programManager.build(t,g),this.programManager.setArtifact($,v),se("info",()=>`[artifact] key: ${$}, programName: ${t.name}`)),m&&v.uniformVariablesInfo){if(m.length!==v.uniformVariablesInfo.length)throw new Error(`Uniform variables count mismatch: expect ${v.uniformVariablesInfo.length}, got ${m.length} in program "${v.programInfo.name}".`);for(let S=0;S<m.length;S++){let T=m[S],A=T.type,C=typeof T.data=="number"?1:T.data.length,[P,D]=v.uniformVariablesInfo[S];if(A!==P||C!==D)throw new Error(`Uniform variable ${S} mismatch: expect type ${P} with size ${D}, got type ${A} with size ${C} in program "${v.programInfo.name}".`)}}if(se("info",()=>`[ProgramManager] run "${t.name}" (key=${$}) with ${g[0]}x${g[1]}x${g[2]}`),this.queryType!=="none"||this.sessionStatus==="capturing"){let S={kernelId:this.currentKernelId,programName:v.programInfo.name,inputTensorViews:r,outputTensorViews:h};this.pendingKernels.push(S),this.sessionStatus==="capturing"&&this.capturedPendingKernels.get(this.currentSessionId).push(S)}return this.programManager.run(v,d,_,g,y),Be(t.name),h}upload(t,r){this.gpuDataManager.upload(t,r)}memcpy(t,r){this.gpuDataManager.memcpy(t,r)}async download(t,r){await this.gpuDataManager.download(t,r)}alloc(t){return this.gpuDataManager.create(t).id}free(t){return this.gpuDataManager.release(t)}createKernel(t,r,n,o){let i=Zl.get(t);if(!i)throw new Error(`kernel not implemented: ${t}`);let a={kernelType:t,kernelName:o,kernelEntry:i[0],attributes:[i[1],n]};this.kernels.set(r,a)}releaseKernel(t){let r=this.kernelPersistentData.get(t);if(r){for(let n of r)this.gpuDataManager.release(n.id);this.kernelPersistentData.delete(t)}this.kernelCustomData.delete(t),this.kernels.delete(t)}computeKernel(t,r,n){let o=this.kernels.get(t);if(!o)throw new Error(`kernel not created: ${t}`);let i=o.kernelType,a=o.kernelName,d=o.kernelEntry,l=o.attributes;if(this.currentKernelId!==null)throw new Error(`kernel "[${i}] ${a}" is not allowed to be called recursively`);this.currentKernelId=t,l[0]&&(l[1]=l[0](l[1]),l[0]=void 0),se("info",()=>`[WebGPU] Start to run kernel "[${i}] ${a}"...`);let p=this.env.debug;this.temporaryData=[];try{return p&&this.device.pushErrorScope("validation"),d(r,l[1]),0}catch(m){return n.push(Promise.resolve(`[WebGPU] Kernel "[${i}] ${a}" failed. ${m}`)),1}finally{p&&n.push(this.device.popErrorScope().then(m=>m?`GPU validation error for kernel "[${i}] ${a}": ${m.message}`:null));for(let m of this.temporaryData)this.gpuDataManager.release(m.id);this.temporaryData=[],this.currentKernelId=null}}registerBuffer(t,r,n,o){let i=this.sessionExternalDataMapping.get(t);i||(i=new Map,this.sessionExternalDataMapping.set(t,i));let a=i.get(r),d=this.gpuDataManager.registerExternalBuffer(n,o,a);return i.set(r,[d,n]),d}unregisterBuffers(t){let r=this.sessionExternalDataMapping.get(t);r&&(r.forEach(n=>this.gpuDataManager.unregisterExternalBuffer(n[0])),this.sessionExternalDataMapping.delete(t))}getBuffer(t){let r=this.gpuDataManager.get(t);if(!r)throw new Error(`no GPU data for buffer: ${t}`);return r.buffer}createDownloader(t,r,n){return async()=>{let o=await ro(this,t,r);return Rr(o.buffer,n)}}writeTimestamp(t){this.queryType==="inside-passes"&&this.computePassEncoder.writeTimestamp(this.querySet,t)}setQueryType(){this.queryType="none",(this.env.webgpu.profiling?.mode==="default"||(typeof this.env.trace>"u"?this.env.wasm.trace:this.env.trace))&&(this.device.features.has("chromium-experimental-timestamp-query-inside-passes")?this.queryType="inside-passes":this.device.features.has("timestamp-query")&&(this.queryType="at-passes"),this.queryType!=="none"&&typeof this.querySet>"u"&&(this.querySet=this.device.createQuerySet({type:"timestamp",count:this.maxDispatchNumber*2}),this.queryResolveBuffer=this.device.createBuffer({size:this.maxDispatchNumber*2*8,usage:GPUBufferUsage.COPY_SRC|GPUBufferUsage.QUERY_RESOLVE})))}captureBegin(){se("info","captureBegin"),this.capturedCommandList.get(this.currentSessionId)||this.capturedCommandList.set(this.currentSessionId,[]),this.capturedPendingKernels.get(this.currentSessionId)||this.capturedPendingKernels.set(this.currentSessionId,[]),this.flush(),this.sessionStatus="capturing"}captureEnd(){se("info","captureEnd"),this.flush(),this.sessionStatus="default"}replay(){se("info","replay"),this.sessionStatus="replaying";let t=this.capturedCommandList.get(this.currentSessionId),r=this.capturedPendingKernels.get(this.currentSessionId),n=t.length;this.pendingKernels=[];for(let o=0;o<n;o++){let i=this.getComputePassEncoder(),a=t[o];this.writeTimestamp(this.pendingDispatchNumber*2),i.setPipeline(a.computePipeline),i.setBindGroup(0,a.bindGroup),i.dispatchWorkgroups(...a.dispatchGroup),this.writeTimestamp(this.pendingDispatchNumber*2+1),this.pendingDispatchNumber++,this.queryType!=="none"&&this.pendingKernels.push(r[o]),(this.pendingDispatchNumber>=this.maxDispatchNumber||this.queryType==="at-passes")&&this.endComputePass(),this.pendingDispatchNumber>=this.maxDispatchNumber&&this.flush()}this.flush(),this.sessionStatus="default"}onCreateSession(){this.gpuDataManager.onCreateSession()}onReleaseSession(t){this.unregisterBuffers(t),this.capturedCommandList.has(t)&&this.capturedCommandList.delete(t),this.capturedPendingKernels.has(t)&&this.capturedPendingKernels.delete(t),this.gpuDataManager.onReleaseSession(t)}onRunStart(t){this.currentSessionId=t,this.setQueryType()}}});var lg,ec,cg,tc,on,an,Ao,rc,nc=U(()=>{"use strict";et();lg=1,ec=()=>lg++,cg=new Map([["float32",32],["float16",16],["int32",32],["uint32",32],["int64",64],["uint64",64],["int8",8],["uint8",8],["int4",4],["uint4",4]]),tc=(e,t)=>{let r=cg.get(e);if(!r)throw new Error("Unsupported data type.");return t.length>0?Math.ceil(t.reduce((n,o)=>n*o)*r/8):0},on=class{constructor(t){this.sessionId=t.sessionId,this.mlContext=t.context,this.mlTensor=t.tensor,this.dataType=t.dataType,this.tensorShape=t.shape}get tensor(){return this.mlTensor}get type(){return this.dataType}get shape(){return this.tensorShape}get byteLength(){return tc(this.dataType,this.tensorShape)}destroy(){se("verbose",()=>"[WebNN] TensorWrapper.destroy"),this.mlTensor.destroy()}write(t){this.mlContext.writeTensor(this.mlTensor,t)}async read(t){return t?this.mlContext.readTensor(this.mlTensor,t):this.mlContext.readTensor(this.mlTensor)}canReuseTensor(t,r,n){return this.mlContext===t&&this.dataType===r&&this.tensorShape.length===n.length&&this.tensorShape.every((o,i)=>o===n[i])}},an=class{constructor(t,r){this.tensorManager=t;this.wrapper=r}get tensorWrapper(){return this.wrapper}releaseTensor(){this.tensorWrapper&&(this.tensorManager.releaseTensor(this.tensorWrapper),this.wrapper=void 0)}async ensureTensor(t,r,n,o){if(this.wrapper){if(this.wrapper.canReuseTensor(t,r,n))return this.wrapper.tensor;if(o){if(this.wrapper.byteLength!==tc(r,n))throw new Error("Unable to copy data to tensor with different size.");this.activeUpload=new Uint8Array(await this.wrapper.read())}this.tensorManager.releaseTensor(this.wrapper)}let i=typeof MLTensorUsage>"u"?void 0:MLTensorUsage.READ|MLTensorUsage.WRITE;return this.wrapper=await this.tensorManager.getCachedTensor(r,n,i,!0,!0),o&&this.activeUpload&&(this.wrapper.write(this.activeUpload),this.activeUpload=void 0),this.wrapper.tensor}upload(t){if(this.wrapper)if(t.byteLength===this.wrapper.byteLength){this.wrapper.write(t);return}else se("verbose",()=>"Data size does not match tensor size. Releasing tensor."),this.releaseTensor();this.activeUpload?this.activeUpload.set(t):this.activeUpload=new Uint8Array(t)}async download(t){if(this.activeUpload)if(t){t instanceof ArrayBuffer?new Uint8Array(t).set(this.activeUpload):new Uint8Array(t.buffer,t.byteOffset,t.byteLength).set(this.activeUpload);return}else return this.activeUpload.buffer;if(!this.wrapper)throw new Error("Tensor has not been created.");return t?this.wrapper.read(t):this.wrapper.read()}},Ao=class{constructor(t){this.backend=t;this.tensorTrackersById=new Map;this.freeTensors=[];this.externalTensors=new Set}reserveTensorId(){let t=ec();return this.tensorTrackersById.set(t,new an(this)),t}releaseTensorId(t){let r=this.tensorTrackersById.get(t);r&&(this.tensorTrackersById.delete(t),r.tensorWrapper&&this.releaseTensor(r.tensorWrapper))}async ensureTensor(t,r,n,o){se("verbose",()=>`[WebNN] TensorManager.ensureTensor {tensorId: ${t}, dataType: ${r}, shape: ${n}, copyOld: ${o}}`);let i=this.tensorTrackersById.get(t);if(!i)throw new Error("Tensor not found.");return i.ensureTensor(this.backend.currentContext,r,n,o)}upload(t,r){let n=this.tensorTrackersById.get(t);if(!n)throw new Error("Tensor not found.");n.upload(r)}async download(t,r){se("verbose",()=>`[WebNN] TensorManager.download {tensorId: ${t}, dstBuffer: ${r?.byteLength}}`);let n=this.tensorTrackersById.get(t);if(!n)throw new Error("Tensor not found.");return n.download(r)}releaseTensorsForSession(t){for(let r of this.freeTensors)r.sessionId===t&&r.destroy();this.freeTensors=this.freeTensors.filter(r=>r.sessionId!==t)}registerTensor(t,r,n,o){let i=ec(),a=new on({sessionId:this.backend.currentSessionId,context:t,tensor:r,dataType:n,shape:o});return this.tensorTrackersById.set(i,new an(this,a)),this.externalTensors.add(a),i}async getCachedTensor(t,r,n,o,i){let a=this.backend.currentSessionId,d=this.backend.currentContext;for(let[p,m]of this.freeTensors.entries())if(m.canReuseTensor(d,t,r)){se("verbose",()=>`[WebNN] Reusing tensor {dataType: ${t}, shape: ${r}}`);let u=this.freeTensors.splice(p,1)[0];return u.sessionId=a,u}se("verbose",()=>`[WebNN] MLContext.createTensor {dataType: ${t}, shape: ${r}}`);let l=await d.createTensor({dataType:t,shape:r,dimensions:r,usage:n,writable:o,readable:i});return new on({sessionId:a,context:d,tensor:l,dataType:t,shape:r})}releaseTensor(t){this.externalTensors.has(t)&&this.externalTensors.delete(t),this.freeTensors.push(t)}},rc=(...e)=>new Ao(...e)});var oc,pg,sn,ic=U(()=>{"use strict";J();gt();Xn();nc();et();oc=new Map([[1,"float32"],[10,"float16"],[6,"int32"],[12,"uint32"],[7,"int64"],[13,"uint64"],[22,"int4"],[21,"uint4"],[3,"int8"],[2,"uint8"],[9,"uint8"]]),pg=(e,t)=>{if(e===t)return!0;if(e===void 0||t===void 0)return!1;let r=Object.keys(e).sort(),n=Object.keys(t).sort();return r.length===n.length&&r.every((o,i)=>o===n[i]&&e[o]===t[o])},sn=class{constructor(t){this.tensorManager=rc(this);this.mlContextBySessionId=new Map;this.sessionIdsByMLContext=new Map;this.mlContextCache=[];Mr(t.logLevel,!!t.debug)}get currentSessionId(){if(this.activeSessionId===void 0)throw new Error("No active session");return this.activeSessionId}onRunStart(t){this.activeSessionId=t}async createMLContext(t){if(t instanceof GPUDevice){let n=this.mlContextCache.findIndex(o=>o.gpuDevice===t);if(n!==-1)return this.mlContextCache[n].mlContext;{let o=await navigator.ml.createContext(t);return this.mlContextCache.push({gpuDevice:t,mlContext:o}),o}}else if(t===void 0){let n=this.mlContextCache.findIndex(o=>o.options===void 0&&o.gpuDevice===void 0);if(n!==-1)return this.mlContextCache[n].mlContext;{let o=await navigator.ml.createContext();return this.mlContextCache.push({mlContext:o}),o}}let r=this.mlContextCache.findIndex(n=>pg(n.options,t));if(r!==-1)return this.mlContextCache[r].mlContext;{let n=await navigator.ml.createContext(t);return this.mlContextCache.push({options:t,mlContext:n}),n}}get currentContext(){let t=this.getMLContext(this.currentSessionId);if(!t)throw new Error(`No MLContext found for session ${this.currentSessionId}`);return t}registerMLContext(t,r){this.mlContextBySessionId.set(t,r);let n=this.sessionIdsByMLContext.get(r);n||(n=new Set,this.sessionIdsByMLContext.set(r,n)),n.add(t)}onReleaseSession(t){let r=this.mlContextBySessionId.get(t);if(!r)return;this.tensorManager.releaseTensorsForSession(t),this.mlContextBySessionId.delete(t);let n=this.sessionIdsByMLContext.get(r);if(n.delete(t),n.size===0){this.sessionIdsByMLContext.delete(r);let o=this.mlContextCache.findIndex(i=>i.mlContext===r);o!==-1&&this.mlContextCache.splice(o,1)}}getMLContext(t){return this.mlContextBySessionId.get(t)}reserveTensorId(){return this.tensorManager.reserveTensorId()}releaseTensorId(t){se("verbose",()=>`[WebNN] releaseTensorId {tensorId: ${t}}`),this.tensorManager.releaseTensorId(t)}async ensureTensor(t,r,n,o){let i=oc.get(r);if(!i)throw new Error(`Unsupported ONNX data type: ${r}`);return this.tensorManager.ensureTensor(t,i,n,o)}uploadTensor(t,r){if(!Te().shouldTransferToMLTensor)throw new Error("Trying to upload to a MLTensor while shouldTransferToMLTensor is false");se("verbose",()=>`[WebNN] uploadTensor {tensorId: ${t}, data: ${r.byteLength}}`),this.tensorManager.upload(t,r)}async downloadTensor(t,r){return this.tensorManager.download(t,r)}createMLTensorDownloader(t,r){return async()=>{let n=await this.tensorManager.download(t);return Rr(n,r)}}registerMLTensor(t,r,n){let o=oc.get(r);if(!o)throw new Error(`Unsupported ONNX data type: ${r}`);let i=this.tensorManager.registerTensor(this.currentContext,t,o,n);return se("verbose",()=>`[WebNN] registerMLTensor {tensor: ${t}, dataType: ${o}, dimensions: ${n}} -> {tensorId: ${i}}`),i}registerMLConstant(t,r,n,o,i,a){if(!a)throw new Error("External mounted files are not available.");let d=t;t.startsWith("./")&&(d=t.substring(2));let l=a.get(d);if(!l)throw new Error(`File with name ${d} not found in preloaded files.`);if(r+n>l.byteLength)throw new Error("Out of bounds: data offset and length exceed the external file data size.");let p=l.slice(r,r+n).buffer,m;switch(i.dataType){case"float32":m=new Float32Array(p);break;case"float16":m=new Uint16Array(p);break;case"int32":m=new Int32Array(p);break;case"uint32":m=new Uint32Array(p);break;case"int64":m=new BigInt64Array(p);break;case"uint64":m=new BigUint64Array(p);break;case"int8":m=new Int8Array(p);break;case"int4":case"uint4":case"uint8":m=new Uint8Array(p);break;default:throw new Error(`Unsupported data type: ${i.dataType} in creating WebNN Constant from external data.`)}return se("verbose",()=>`[WebNN] registerMLConstant {dataType: ${i.dataType}, shape: ${i.shape}}}`),o.constant(i,m)}flush(){}}});var ac={};Ht(ac,{init:()=>mg});var tr,ko,mg,sc=U(()=>{"use strict";J();Jl();et();ne();ic();tr=class e{constructor(t,r,n,o){this.module=t;this.dataType=r;this.data=n;this.dims=o}getFloat32Array(){if(this.dataType!==1)throw new Error("Invalid data type");let t=k.size(this.dims);return t===0?new Float32Array:new Float32Array(this.module.HEAP8.buffer,this.data,t)}getBigInt64Array(){if(this.dataType!==7)throw new Error("Invalid data type");let t=k.size(this.dims);return t===0?new BigInt64Array:new BigInt64Array(this.module.HEAP8.buffer,this.data,t)}getInt32Array(){if(this.dataType!==6)throw new Error("Invalid data type");let t=k.size(this.dims);return t===0?new Int32Array:new Int32Array(this.module.HEAP8.buffer,this.data,t)}getUint16Array(){if(this.dataType!==10&&this.dataType!==4)throw new Error("Invalid data type");let t=k.size(this.dims);return t===0?new Uint16Array:new Uint16Array(this.module.HEAP8.buffer,this.data,t)}reshape(t){if(k.size(t)!==k.size(this.dims))throw new Error("Invalid new shape");return new e(this.module,this.dataType,this.data,t)}},ko=class{constructor(t,r,n){this.module=t;this.backend=r;this.customDataOffset=0;this.customDataSize=0;this.adapterInfo=r.adapterInfo,this.deviceInfo=r.deviceInfo;let o=t.PTR_SIZE,i=n/t.PTR_SIZE,a=o===4?"i32":"i64";this.opKernelContext=Number(t.getValue(o*i++,a));let d=Number(t.getValue(o*i++,a));this.outputCount=Number(t.getValue(o*i++,a)),this.customDataOffset=Number(t.getValue(o*i++,"*")),this.customDataSize=Number(t.getValue(o*i++,a));let l=[];for(let p=0;p<d;p++){let m=Number(t.getValue(o*i++,a)),u=Number(t.getValue(o*i++,"*")),h=Number(t.getValue(o*i++,a)),_=[];for(let y=0;y<h;y++)_.push(Number(t.getValue(o*i++,a)));l.push(new tr(t,m,u,_))}this.inputs=l}get kernelCustomData(){return this.backend.currentKernelCustomData}get customDataBuffer(){return this.module.HEAPU8.subarray(this.customDataOffset,this.customDataOffset+this.customDataSize)}compute(t,r){let n=r?.inputs?.map(d=>typeof d=="number"?this.inputs[d]:d)??this.inputs,o=r?.outputs??[],i=(d,l,p)=>new tr(this.module,l,this.output(d,p),p),a=(d,l)=>{let p=At(d,l);if(!p)throw new Error(`Unsupported data type: ${d}`);let m=p>0?this.backend.gpuDataManager.create(p).id:0;return new tr(this.module,d,m,l)};return this.backend.run(t,n,o,i,a,this.outputCount)}output(t,r){let n=this.module.stackSave();try{let o=this.module.PTR_SIZE,i=o===4?"i32":"i64",a=this.module.stackAlloc((1+r.length)*o);this.module.setValue(a,r.length,i);for(let d=0;d<r.length;d++)this.module.setValue(a+o*(d+1),r[d],i);return this.module._JsepOutput(this.opKernelContext,t,a)}catch(o){throw new Error(`Failed to generate kernel's output[${t}] with dims [${r}]. If you are running with pre-allocated output, please make sure the output type/dims are correct. Error: ${o}`)}finally{this.module.stackRestore(n)}}},mg=async(e,t,r,n)=>{let o=t.jsepInit;if(!o)throw new Error("Failed to initialize JSEP. The WebAssembly module is not built with JSEP support.");if(e==="webgpu"){let i=new nn;await i.initialize(r,n),o("webgpu",[i,a=>i.alloc(Number(a)),a=>i.free(a),(a,d,l,p=!1)=>{if(p)se("verbose",()=>`[WebGPU] jsepCopyGpuToGpu: src=${Number(a)}, dst=${Number(d)}, size=${Number(l)}`),i.memcpy(Number(a),Number(d));else{se("verbose",()=>`[WebGPU] jsepCopyCpuToGpu: dataOffset=${Number(a)}, gpuDataId=${Number(d)}, size=${Number(l)}`);let m=t.HEAPU8.subarray(Number(a>>>0),Number(a>>>0)+Number(l));i.upload(Number(d),m)}},async(a,d,l)=>{se("verbose",()=>`[WebGPU] jsepCopyGpuToCpu: gpuDataId=${a}, dataOffset=${d}, size=${l}`),await i.download(Number(a),()=>t.HEAPU8.subarray(Number(d)>>>0,Number(d+l)>>>0))},(a,d,l)=>i.createKernel(a,Number(d),l,t.UTF8ToString(t._JsepGetNodeName(Number(d)))),a=>i.releaseKernel(a),(a,d,l,p)=>{se("verbose",()=>`[WebGPU] jsepRun: sessionHandle=${l}, kernel=${a}, contextDataOffset=${d}`);let m=new ko(t,i,Number(d));return i.computeKernel(Number(a),m,p)},()=>i.captureBegin(),()=>i.captureEnd(),()=>i.replay()])}else{let i=new sn(r);o("webnn",[i,()=>i.reserveTensorId(),a=>i.releaseTensorId(a),async(a,d,l,p)=>i.ensureTensor(a,d,l,p),(a,d)=>{i.uploadTensor(a,d)},async(a,d)=>i.downloadTensor(a,d)])}}});var fg,Sr,Tr,zt,hg,qt,Ir,Cr,uc,Ar,kr,Er,Fn=U(()=>{"use strict";Ga();Fa();J();gt();zr();Qn();fg=(e,t)=>{Te()._OrtInit(e,t)!==0&&ce("Can't initialize onnxruntime.")},Sr=async e=>{fg(e.wasm.numThreads,Yt(e.logLevel))},Tr=async(e,t)=>{{let r=(sc(),gr(ac)).init;if(t==="webgpu"){if(typeof navigator>"u"||!navigator.gpu)throw new Error("WebGPU is not supported in current environment");let n=e.webgpu.adapter;if(n){if(typeof n.limits!="object"||typeof n.features!="object"||typeof n.requestDevice!="function")throw new Error("Invalid GPU adapter set in `env.webgpu.adapter`. It must be a GPUAdapter object.")}else{let o=e.webgpu.powerPreference;if(o!==void 0&&o!=="low-power"&&o!=="high-performance")throw new Error(`Invalid powerPreference setting: "${o}"`);let i=e.webgpu.forceFallbackAdapter;if(i!==void 0&&typeof i!="boolean")throw new Error(`Invalid forceFallbackAdapter setting: "${i}"`);if(n=await navigator.gpu.requestAdapter({powerPreference:o,forceFallbackAdapter:i}),!n)throw new Error('Failed to get GPU adapter. You may need to enable flag "--enable-unsafe-webgpu" if you are using Chrome.')}await r("webgpu",Te(),e,n)}if(t==="webnn"){if(typeof navigator>"u"||!navigator.ml)throw new Error("WebNN is not supported in current environment");await r("webnn",Te(),e)}}},zt=new Map,hg=e=>{let t=Te(),r=t.stackSave();try{let n=t.PTR_SIZE,o=t.stackAlloc(2*n);t._OrtGetInputOutputCount(e,o,o+n)!==0&&ce("Can't get session input/output count.");let a=n===4?"i32":"i64";return[Number(t.getValue(o,a)),Number(t.getValue(o+n,a))]}finally{t.stackRestore(r)}},qt=e=>{let t=Te(),r=t._malloc(e.byteLength);if(r===0)throw new Error(`Can't create a session. failed to allocate a buffer of size ${e.byteLength}.`);return t.HEAPU8.set(e,r),[r,e.byteLength]},Ir=async(e,t)=>{let r,n,o=Te();Array.isArray(e)?[r,n]=e:e.buffer===o.HEAPU8.buffer?[r,n]=[e.byteOffset,e.byteLength]:[r,n]=qt(e);let i=0,a=0,d=0,l=[],p=[],m=[];try{if([a,l]=Ha(t),t?.externalData&&o.mountExternalData){let v=[];for(let S of t.externalData){let T=typeof S=="string"?S:S.path;v.push(Zt(typeof S=="string"?S:S.data).then(A=>{o.mountExternalData(T,A)}))}await Promise.all(v)}for(let v of t?.executionProviders??[])if((typeof v=="string"?v:v.name)==="webnn"){if(o.shouldTransferToMLTensor=!1,typeof v!="string"){let T=v,A=T?.context,C=T?.gpuDevice,P=T?.deviceType,D=T?.powerPreference;A?o.currentContext=A:C?o.currentContext=await o.jsepCreateMLContext(C):o.currentContext=await o.jsepCreateMLContext({deviceType:P,powerPreference:D})}else o.currentContext=await o.jsepCreateMLContext();break}i=await o._OrtCreateSession(r,n,a),i===0&&ce("Can't create a session."),o.jsepOnCreateSession?.(),o.currentContext&&(o.jsepRegisterMLContext(i,o.currentContext),o.currentContext=void 0,o.shouldTransferToMLTensor=!0);let[u,h]=hg(i),_=!!t?.enableGraphCapture,y=[],g=[],x=[];for(let v=0;v<u;v++){let S=o._OrtGetInputName(i,v);S===0&&ce("Can't get an input name."),p.push(S),y.push(o.UTF8ToString(S))}for(let v=0;v<h;v++){let S=o._OrtGetOutputName(i,v);S===0&&ce("Can't get an output name."),m.push(S);let T=o.UTF8ToString(S);g.push(T);{if(_&&t?.preferredOutputLocation===void 0){x.push("gpu-buffer");continue}let A=typeof t?.preferredOutputLocation=="string"?t.preferredOutputLocation:t?.preferredOutputLocation?.[T]??"cpu";if(A!=="cpu"&&A!=="cpu-pinned"&&A!=="gpu-buffer"&&A!=="ml-tensor")throw new Error(`Not supported preferred output location: ${A}.`);if(_&&A!=="gpu-buffer")throw new Error(`Not supported preferred output location: ${A}. Only 'gpu-buffer' location is supported when enableGraphCapture is true.`);x.push(A)}}let $=null;return x.some(v=>v==="gpu-buffer"||v==="ml-tensor")&&(d=o._OrtCreateBinding(i),d===0&&ce("Can't create IO binding."),$={handle:d,outputPreferredLocations:x,outputPreferredLocationsEncoded:x.map(v=>Zn(v))}),zt.set(i,[i,p,m,$,_,!1]),[i,y,g]}catch(u){throw p.forEach(h=>o._OrtFree(h)),m.forEach(h=>o._OrtFree(h)),d!==0&&o._OrtReleaseBinding(d)!==0&&ce("Can't release IO binding."),i!==0&&o._OrtReleaseSession(i)!==0&&ce("Can't release session."),u}finally{o._free(r),a!==0&&o._OrtReleaseSessionOptions(a)!==0&&ce("Can't release session options."),l.forEach(u=>o._free(u)),o.unmountExternalData?.()}},Cr=e=>{let t=Te(),r=zt.get(e);if(!r)throw new Error(`cannot release session. invalid session id: ${e}`);let[n,o,i,a,d]=r;a&&(d&&t._OrtClearBoundOutputs(a.handle)!==0&&ce("Can't clear bound outputs."),t._OrtReleaseBinding(a.handle)!==0&&ce("Can't release IO binding.")),t.jsepOnReleaseSession?.(e),o.forEach(l=>t._OrtFree(l)),i.forEach(l=>t._OrtFree(l)),t._OrtReleaseSession(n)!==0&&ce("Can't release session."),zt.delete(e)},uc=(e,t,r,n,o,i=!1)=>{if(!e){t.push(0);return}let a=Te(),d=a.PTR_SIZE,l=e[0],p=e[1],m=e[3],u,h;if(l==="string"&&(m==="gpu-buffer"||m==="ml-tensor"))throw new Error("String tensor is not supported on GPU.");if(i&&m!=="gpu-buffer")throw new Error(`External buffer must be provided for input/output index ${o} when enableGraphCapture is true.`);if(m==="gpu-buffer"){let g=e[2].gpuBuffer;h=At(jt(l),p);let x=a.jsepRegisterBuffer;if(!x)throw new Error('Tensor location "gpu-buffer" is not supported without using WebGPU.');u=x(n,o,g,h)}else if(m==="ml-tensor"){let g=e[2].mlTensor;h=At(jt(l),p);let x=a.jsepRegisterMLTensor;if(!x)throw new Error('Tensor location "ml-tensor" is not supported without using WebNN.');u=x(g,jt(l),p)}else{let g=e[2];if(Array.isArray(g)){h=d*g.length,u=a._malloc(h),r.push(u);for(let x=0;x<g.length;x++){if(typeof g[x]!="string")throw new TypeError(`tensor data at index ${x} is not a string`);a.setValue(u+x*d,ke(g[x],r),"*")}}else h=g.byteLength,u=a._malloc(h),r.push(u),a.HEAPU8.set(new Uint8Array(g.buffer,g.byteOffset,h),u)}let _=a.stackSave(),y=a.stackAlloc(4*p.length);try{p.forEach((x,$)=>a.setValue(y+$*d,x,d===4?"i32":"i64"));let g=a._OrtCreateTensor(jt(l),u,h,y,p.length,Zn(m));g===0&&ce(`Can't create tensor for input/output. session=${n}, index=${o}.`),t.push(g)}finally{a.stackRestore(_)}},Ar=async(e,t,r,n,o,i)=>{let a=Te(),d=a.PTR_SIZE,l=zt.get(e);if(!l)throw new Error(`cannot run inference. invalid session id: ${e}`);let p=l[0],m=l[1],u=l[2],h=l[3],_=l[4],y=l[5],g=t.length,x=n.length,$=0,v=[],S=[],T=[],A=[],C=a.stackSave(),P=a.stackAlloc(g*d),D=a.stackAlloc(g*d),R=a.stackAlloc(x*d),H=a.stackAlloc(x*d);try{a.jsepOnRunStart?.(p),[$,v]=La(i);for(let V=0;V<g;V++)uc(r[V],S,A,e,t[V],_);for(let V=0;V<x;V++)uc(o[V],T,A,e,g+n[V],_);for(let V=0;V<g;V++)a.setValue(P+V*d,S[V],"*"),a.setValue(D+V*d,m[t[V]],"*");for(let V=0;V<x;V++)a.setValue(R+V*d,T[V],"*"),a.setValue(H+V*d,u[n[V]],"*");if(h&&!y){let{handle:V,outputPreferredLocations:K,outputPreferredLocationsEncoded:we}=h;if(m.length!==g)throw new Error(`input count from feeds (${g}) is expected to be always equal to model's input count (${m.length}).`);for(let j=0;j<g;j++){let Q=t[j];await a._OrtBindInput(V,m[Q],S[j])!==0&&ce(`Can't bind input[${j}] for session=${e}.`)}for(let j=0;j<x;j++){let Q=n[j];o[j]?.[3]?a._OrtBindOutput(V,u[Q],T[j],0)!==0&&ce(`Can't bind pre-allocated output[${j}] for session=${e}.`):a._OrtBindOutput(V,u[Q],0,we[Q])!==0&&ce(`Can't bind output[${j}] to ${K[j]} for session=${e}.`)}zt.set(e,[p,m,u,h,_,!0])}let L;h?L=await a._OrtRunWithBinding(p,h.handle,x,R,$):L=await a._OrtRun(p,D,P,g,H,x,R,$),L!==0&&ce("failed to call OrtRun().");let re=[];for(let V=0;V<x;V++){let K=Number(a.getValue(R+V*d,"*"));if(K===T[V]){re.push(o[V]);continue}let we=a.stackSave(),j=a.stackAlloc(4*d),Q=!1,ie,te=0;try{a._OrtGetTensorData(K,j,j+d,j+2*d,j+3*d)!==0&&ce(`Can't access output tensor data on index ${V}.`);let Oe=d===4?"i32":"i64",ve=Number(a.getValue(j,Oe));te=a.getValue(j+d,"*");let de=a.getValue(j+d*2,"*"),W=Number(a.getValue(j+d*3,Oe)),Y=[];for(let pe=0;pe<W;pe++)Y.push(Number(a.getValue(de+pe*d,Oe)));a._OrtFree(de)!==0&&ce("Can't free memory for tensor dims.");let he=Y.reduce((pe,Ie)=>pe*Ie,1);ie=bt(ve);let De=h?.outputPreferredLocations[n[V]];if(ie==="string"){if(De==="gpu-buffer"||De==="ml-tensor")throw new Error("String tensor is not supported on GPU.");let pe=[];for(let Ie=0;Ie<he;Ie++){let He=a.getValue(te+Ie*d,"*"),mn=a.getValue(te+(Ie+1)*d,"*"),wt=Ie===he-1?void 0:mn-He;pe.push(a.UTF8ToString(He,wt))}re.push([ie,Y,pe,"cpu"])}else if(De==="gpu-buffer"&&he>0){let pe=a.jsepGetBuffer;if(!pe)throw new Error('preferredLocation "gpu-buffer" is not supported without using WebGPU.');let Ie=pe(te),He=At(ve,he);if(He===void 0||!Dr(ie))throw new Error(`Unsupported data type: ${ie}`);Q=!0,re.push([ie,Y,{gpuBuffer:Ie,download:a.jsepCreateDownloader(Ie,He,ie),dispose:()=>{a._OrtReleaseTensor(K)!==0&&ce("Can't release tensor.")}},"gpu-buffer"])}else if(De==="ml-tensor"&&he>0){let pe=a.jsepEnsureTensor;if(!pe)throw new Error('preferredLocation "ml-tensor" is not supported without using WebNN.');if(At(ve,he)===void 0||!Br(ie))throw new Error(`Unsupported data type: ${ie}`);let He=await pe(te,ve,Y,!1);Q=!0,re.push([ie,Y,{mlTensor:He,download:a.jsepCreateMLTensorDownloader(te,ie),dispose:()=>{a.jsepReleaseTensorId(te),a._OrtReleaseTensor(K)}},"ml-tensor"])}else{let pe=Or(ie),Ie=new pe(he);new Uint8Array(Ie.buffer,Ie.byteOffset,Ie.byteLength).set(a.HEAPU8.subarray(te,te+Ie.byteLength)),re.push([ie,Y,Ie,"cpu"])}}finally{a.stackRestore(we),ie==="string"&&te&&a._free(te),Q||a._OrtReleaseTensor(K)}}return h&&!_&&(a._OrtClearBoundOutputs(h.handle)!==0&&ce("Can't clear bound outputs."),zt.set(e,[p,m,u,h,_,!1])),re}finally{a.stackRestore(C),S.forEach(L=>a._OrtReleaseTensor(L)),T.forEach(L=>a._OrtReleaseTensor(L)),A.forEach(L=>a._free(L)),$!==0&&a._OrtReleaseRunOptions($),v.forEach(L=>a._free(L))}},kr=e=>{let t=Te(),r=zt.get(e);if(!r)throw new Error("invalid session id");let n=r[0],o=t._OrtEndProfiling(n);o===0&&ce("Can't get an profile file name."),t._OrtFree(o)},Er=e=>{let t=[];for(let r of e){let n=r[2];!Array.isArray(n)&&"buffer"in n&&t.push(n.buffer)}return t}});var Ot,Ge,rr,dn,ln,un,Eo,Po,Wt,Lt,bg,dc,lc,cc,pc,mc,fc,hc,zo=U(()=>{"use strict";Le();Fn();gt();$r();Ot=()=>!!_e.wasm.proxy&&typeof document<"u",rr=!1,dn=!1,ln=!1,Po=new Map,Wt=(e,t)=>{let r=Po.get(e);r?r.push(t):Po.set(e,[t])},Lt=()=>{if(rr||!dn||ln||!Ge)throw new Error("worker not ready")},bg=e=>{switch(e.data.type){case"init-wasm":rr=!1,e.data.err?(ln=!0,Eo[1](e.data.err)):(dn=!0,Eo[0]()),un&&(URL.revokeObjectURL(un),un=void 0);break;case"init-ep":case"copy-from":case"create":case"release":case"run":case"end-profiling":{let t=Po.get(e.data.type);e.data.err?t.shift()[1](e.data.err):t.shift()[0](e.data.out);break}default:}},dc=async()=>{if(!dn){if(rr)throw new Error("multiple calls to 'initWasm()' detected.");if(ln)throw new Error("previous call to 'initWasm()' failed.");if(rr=!0,Ot())return new Promise((e,t)=>{Ge?.terminate(),Na().then(([r,n])=>{try{Ge=n,Ge.onerror=i=>t(i),Ge.onmessage=bg,Eo=[e,t];let o={type:"init-wasm",in:_e};!o.in.wasm.wasmPaths&&(r||import.meta.url?.startsWith("file:"))&&(o.in.wasm.wasmPaths={wasm:new URL("ort-wasm-simd-threaded.jsep.wasm",import.meta.url).href}),Ge.postMessage(o),un=r}catch(o){t(o)}},t)});try{await xr(_e.wasm),await Sr(_e),dn=!0}catch(e){throw ln=!0,e}finally{rr=!1}}},lc=async e=>{if(Ot())return Lt(),new Promise((t,r)=>{Wt("init-ep",[t,r]);let n={type:"init-ep",in:{epName:e,env:_e}};Ge.postMessage(n)});await Tr(_e,e)},cc=async e=>Ot()?(Lt(),new Promise((t,r)=>{Wt("copy-from",[t,r]);let n={type:"copy-from",in:{buffer:e}};Ge.postMessage(n,[e.buffer])})):qt(e),pc=async(e,t)=>{if(Ot()){if(t?.preferredOutputLocation)throw new Error('session option "preferredOutputLocation" is not supported for proxy.');return Lt(),new Promise((r,n)=>{Wt("create",[r,n]);let o={type:"create",in:{model:e,options:{...t}}},i=[];e instanceof Uint8Array&&i.push(e.buffer),Ge.postMessage(o,i)})}else return Ir(e,t)},mc=async e=>{if(Ot())return Lt(),new Promise((t,r)=>{Wt("release",[t,r]);let n={type:"release",in:e};Ge.postMessage(n)});Cr(e)},fc=async(e,t,r,n,o,i)=>{if(Ot()){if(r.some(a=>a[3]!=="cpu"))throw new Error("input tensor on GPU is not supported for proxy.");if(o.some(a=>a))throw new Error("pre-allocated output tensor is not supported for proxy.");return Lt(),new Promise((a,d)=>{Wt("run",[a,d]);let l=r,p={type:"run",in:{sessionId:e,inputIndices:t,inputs:l,outputIndices:n,options:i}};Ge.postMessage(p,Er(l))})}else return Ar(e,t,r,n,o,i)},hc=async e=>{if(Ot())return Lt(),new Promise((t,r)=>{Wt("end-profiling",[t,r]);let n={type:"end-profiling",in:e};Ge.postMessage(n)});kr(e)}});var gc,yg,cn,bc=U(()=>{"use strict";Le();zo();J();vr();Qn();gc=(e,t)=>{switch(e.location){case"cpu":return[e.type,e.dims,e.data,"cpu"];case"gpu-buffer":return[e.type,e.dims,{gpuBuffer:e.gpuBuffer},"gpu-buffer"];case"ml-tensor":return[e.type,e.dims,{mlTensor:e.mlTensor},"ml-tensor"];default:throw new Error(`invalid data location: ${e.location} for ${t()}`)}},yg=e=>{switch(e[3]){case"cpu":return new Fe(e[0],e[2],e[1]);case"gpu-buffer":{let t=e[0];if(!Dr(t))throw new Error(`not supported data type: ${t} for deserializing GPU tensor`);let{gpuBuffer:r,download:n,dispose:o}=e[2];return Fe.fromGpuBuffer(r,{dataType:t,dims:e[1],download:n,dispose:o})}case"ml-tensor":{let t=e[0];if(!Br(t))throw new Error(`not supported data type: ${t} for deserializing MLTensor tensor`);let{mlTensor:r,download:n,dispose:o}=e[2];return Fe.fromMLTensor(r,{dataType:t,dims:e[1],download:n,dispose:o})}default:throw new Error(`invalid data location: ${e[3]}`)}},cn=class{async fetchModelAndCopyToWasmMemory(t){return cc(await Zt(t))}async loadModel(t,r){Ne();let n;typeof t=="string"?!1?n=await Zt(t):n=await this.fetchModelAndCopyToWasmMemory(t):n=t,[this.sessionId,this.inputNames,this.outputNames]=await pc(n,r),Be()}async dispose(){return mc(this.sessionId)}async run(t,r,n){Ne();let o=[],i=[];Object.entries(t).forEach(h=>{let _=h[0],y=h[1],g=this.inputNames.indexOf(_);if(g===-1)throw new Error(`invalid input '${_}'`);o.push(y),i.push(g)});let a=[],d=[];Object.entries(r).forEach(h=>{let _=h[0],y=h[1],g=this.outputNames.indexOf(_);if(g===-1)throw new Error(`invalid output '${_}'`);a.push(y),d.push(g)});let l=o.map((h,_)=>gc(h,()=>`input "${this.inputNames[i[_]]}"`)),p=a.map((h,_)=>h?gc(h,()=>`output "${this.outputNames[d[_]]}"`):null),m=await fc(this.sessionId,i,l,d,p,n),u={};for(let h=0;h<m.length;h++)u[this.outputNames[d[h]]]=a[h]??yg(m[h]);return Be(),u}startProfiling(){}endProfiling(){hc(this.sessionId)}}});var _c={};Ht(_c,{OnnxruntimeWebAssemblyBackend:()=>pn,initializeFlags:()=>yc,wasmBackend:()=>_g});var yc,pn,_g,wc=U(()=>{"use strict";Le();zo();bc();yc=()=>{if((typeof _e.wasm.initTimeout!="number"||_e.wasm.initTimeout<0)&&(_e.wasm.initTimeout=0),_e.wasm.simd===!1&&console.warn('Deprecated property "env.wasm.simd" is set to false. non-SIMD build is no longer provided, and this setting will be ignored.'),typeof _e.wasm.proxy!="boolean"&&(_e.wasm.proxy=!1),typeof _e.wasm.trace!="boolean"&&(_e.wasm.trace=!1),typeof _e.wasm.numThreads!="number"||!Number.isInteger(_e.wasm.numThreads)||_e.wasm.numThreads<=0)if(typeof self<"u"&&!self.crossOriginIsolated)_e.wasm.numThreads=1;else{let e=typeof navigator>"u"?Un("node:os").cpus().length:navigator.hardwareConcurrency;_e.wasm.numThreads=Math.min(4,Math.ceil((e||1)/2))}},pn=class{async init(t){yc(),await dc(),await lc(t)}async createInferenceSessionHandler(t,r){let n=new cn;return await n.loadModel(t,r),Promise.resolve(n)}},_g=new pn});Le();Le();Le();var Ia="1.21.0-dev.20250206-d981b153d3";var $1=Hn;{let e=(wc(),gr(_c)).wasmBackend;Tt("webgpu",e,5),Tt("webnn",e,5),Tt("cpu",e,10),Tt("wasm",e,10)}Object.defineProperty(_e.versions,"web",{value:Ia,enumerable:!0});export{Fp as InferenceSession,_r as TRACE,Ne as TRACE_FUNC_BEGIN,Be as TRACE_FUNC_END,Fe as Tensor,$1 as default,_e as env,Tt as registerBackend};
/**
 * @license
 * Copyright 2021 Google LLC. All Rights Reserved.
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 * =============================================================================
 */
/**
 * @license
 * Copyright 2020 Google LLC. All Rights Reserved.
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 * =============================================================================
 */
/**
 * @license
 * Copyright 2019 Google LLC. All Rights Reserved.
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 * =============================================================================
 */
//# sourceMappingURL=ort.bundle.min.mjs.map
