const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const context = vm.createContext({
    document: { addEventListener() {} },
    window: { addEventListener() {} },
});
vm.runInContext(fs.readFileSync(path.join(__dirname, '../static/dashboard.js'), 'utf8'), context);
const point = time => context.prepareTransactionPoints([
    { date: '2026-11-01', time, amount: 30, category: '饮食*' },
])[0];

for (const [input, expected] of [
    ['2118', 21.3], ['0517', 5 + 17 / 60], ['517', 5 + 17 / 60],
    ['0000', 0], ['2359', 23 + 59 / 60], [' 1506 ', 15.1],
    ['21:18', 21.3], ['5:17', 5 + 17 / 60],
    ['15:00:30', 15 + 30 / 3600], ['150030', 15 + 30 / 3600],
]) {
    assert.equal(point(input).hour, expected, `time: ${input}`);
}
assert.equal(point('0517').time, '05:17');
for (const input of ['', null, undefined, '2400', '2360', '23:59:60', '246000', 'abcd']) {
    assert.equal(point(input).hour, null, `invalid time: ${input}`);
}
assert.equal(context.prepareTransactionPoints([
    { date: '2026-02-30', time: '2118', amount: 30 },
]).length, 0);
console.log('PASS: compact and colon-separated times; midnight; invalid times and dates');
