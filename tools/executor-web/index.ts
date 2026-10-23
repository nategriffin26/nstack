// Executor app `web`: `web mcp` (search, read) for bots and agents that reach tools through Executor.
// Executor's local MCP bridge (127.0.0.1:4313) runs it from ~/.executor/v2/local-mcp.json, servers.web:
//   {"command": "python3", "args": ["<repo>/tools/web.py", "mcp"], "env": {"WEB_LANE": "executor"}}
// Deploy: ~/Projects/executor/deploy.sh web (or executor apps deploy --app <web app id> --files tools/executor-web)
// The provider's name, hosts and fields are its identity: Executor's saved bridge account belongs to exactly this
// definition. The key is 64 characters; since apps beta.95 a string's JSON Schema minLength is half the declared
// length, so 64 here writes the same definition (minLength 32) the account was saved under.
import { defineApp, defineProvider, object, router, secrets, string, withApprovals } from 'apps';
import { mcpHealth, mcpRouter } from 'apps/mcp';
import { never } from 'apps/operations/approval';

const url = 'http://127.0.0.1:4313/mcp/web';
const headers = (account: { fields: { token: string } }) => ({ Authorization: 'Bearer ' + account.fields.token });
const service = defineProvider({
  name: 'Context Local MCP',
  hosts: ['127.0.0.1:4313'],
  auth: { apiKey: secrets({ label: 'Local MCP bridge key', fields: object({ token: string({ minLength: 64 }) }) }) },
  health: (check) => mcpHealth(check, { url, headers: headers(check.account) }),
});

// Searching and reading public pages spends nothing and sends nothing as anyone, so no call asks. The factory also
// runs without a caller (app-scope work), which has no bridge account and so no tools.
export default defineApp({ user: { accounts: { service } } }, async ({ user, signal, cache }) => ({
  tools: user ? withApprovals(await mcpRouter({ url, account: user.accounts.service, headers: headers(user.accounts.service), signal, cache }), () => never()) : router({}),
}));
