import { marked } from 'marked';

const r1 = /^\$(?!\s)([^$\n]*?[^\s$])\$/;
const str = "$100 a month for domains, workspaces, and sequencers) isn't going to work. But since you are a developer and know how to write Python, you can bypass the expensive software and do this for about $15 total.";

console.log(r1.exec(str));

const r2 = /^\$(?!\s)([^$\n]+?)(?<!\s)\$/;
console.log(r2.exec(str));

