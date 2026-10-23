// Executor app `web`: `web mcp` (search, read) for bots and agents that reach tools through Executor.
// Executor's local MCP bridge (127.0.0.1:4313) runs it from ~/.executor/v2/local-mcp.json, servers.web:
//   {"command": "python3", "args": ["<repo>/tools/web.py", "mcp"], "env": {"WEB_LANE": "executor"}}
// Deploy: executor apps deploy --app <web app id> --files tools/executor-web
// The provider keeps the bridge's existing name, key field and apps version (beta.34) so the saved bridge account binds;
// apps beta.95 renders the same key field with a different minLength and the account no longer matches.
import { defineApp, defineProvider, object, secrets, string, withApprovals } from 'apps';
import { mcpHealth, mcpRouter } from 'apps/mcp';
import { never } from 'apps/operations/approval';

const url = 'http://127.0.0.1:4313/mcp/web';
const headers = (account: { fields: { token: string } }) => ({ Authorization: 'Bearer ' + account.fields.token });
const service = defineProvider({
  name: 'Context Local MCP',
  hosts: ['127.0.0.1:4313'],
  auth: { apiKey: secrets({ label: 'Local MCP bridge key', fields: object({ token: string({ minLength: 32 }) }) }) },
  health: (check) => mcpHealth(check, { url, headers: headers(check.account) }),
});

// Searching and reading public pages spends nothing and sends nothing as anyone, so no call asks.
export default defineApp({ accounts: { service } }, async ({ accounts, signal, cache }) => ({
  tools: withApprovals(await mcpRouter({ url, account: accounts.service, headers: headers(accounts.service), signal, cache }), () => never()),
}));
