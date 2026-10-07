const fs=require('node:fs');
const path=require('node:path');
const data=JSON.parse(fs.readFileSync(path.join(__dirname,'design-definition.json'),'utf8'));
fs.writeFileSync(path.join(__dirname,'definition.js'),'// Generated offline bundle. Rebuild with node build-definition.cjs.\nwindow.TokenVisualDefinition = '+JSON.stringify(data,null,2)+';\n');
