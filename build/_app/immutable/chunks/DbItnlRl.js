var o={"+":"inserted","-":"deleted","@":"meta"};const r={name:"diff",token:function(n){var e=n.string.search(/[\t ]+?$/);if(!n.sol()||e===0)return n.skipToEnd(),("error "+(o[n.string.charAt(0)]||"")).replace(/ $/,"");var i=o[n.peek()]||n.skipToEnd();return e===-1?n.skipToEnd():n.pos=e,i}};export{r as diff};
//# sourceMappingURL=DbItnlRl.js.map
