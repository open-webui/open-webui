const tests = [
    "$100 a month for domains... for about $15 total",
    "math $x = 2$ is fast",
    "math $ x = 2 $ is fast",
    "$E=mc^2$",
    "Price is $100.",
    "Cost $100 and $200",
    "Formula $\\alpha_1$"
];

const r1 = /^\$([^$\n]+?)\$/;
const r2 = /^\$([^\s$](?:[^$\n]*?[^\s$])?)\$/;
const r3 = /^\$(?!\s)([^$\n]+?)(?<!\s)\$(?!\d)/;

console.log("Rule 2 /^[^\s$](?:[^$\n]*?[^\s$])?$/:");
for (let t of tests) {
    let match = r2.exec(t.match(/\$.*/) ? t.match(/\$.*/)[0] : "");
    console.log(t, "=>", match ? match[0] : null);
}

console.log("\nRule 3 /^\$(?!\s)([^$\n]+?)(?<!\s)\$(?!\d)/:");
for (let t of tests) {
    let match = r3.exec(t.match(/\$.*/) ? t.match(/\$.*/)[0] : "");
    console.log(t, "=>", match ? match[0] : null);
}
