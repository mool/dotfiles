# Zabbix 5.4 API quick reference

This skill supports only the following Zabbix 5.4 API methods. API tokens are passed in the JSON-RPC `auth` member for this compatibility target.

| Method | Purpose | Fixed/default parameters used by the helper | Official Zabbix 5.4 documentation |
|---|---|---|---|
| `apiinfo.version` | Check server API version without authentication | `params: {}` | [apiinfo.version](https://www.zabbix.com/documentation/5.4/en/manual/api/reference/apiinfo/version) |
| `problem.get` | Retrieve current active problems | `recent: false`; default extended output, acknowledgements, tags, and suppression data; descending `eventid` sort | [problem.get](https://www.zabbix.com/documentation/5.4/en/manual/api/reference/problem/get) |
| `event.get` | Retrieve historical problem events in a bounded interval | Fixed `source: 0`, `object: 0`, `value: 1`, with required `time_from` and `time_till`; descending `clock`, `eventid` sort | [event.get](https://www.zabbix.com/documentation/5.4/en/manual/api/reference/event/get) |
| `host.get` | Query monitored hosts | Default host identity/status output and interface selection | [host.get](https://www.zabbix.com/documentation/5.4/en/manual/api/reference/host/get) |
| `host.create` | Create a monitored host after payload-specific approval | Caller supplies a complete params object or nonempty list of objects | [host.create](https://www.zabbix.com/documentation/5.4/en/manual/api/reference/host/create) |
| `host.update` | Update a monitored host after payload-specific approval | Caller supplies a complete params object or nonempty list of objects | [host.update](https://www.zabbix.com/documentation/5.4/en/manual/api/reference/host/update) |
| API tokens | Authenticate supported calls | Token comes only from `ZABBIX_API_TOKEN` and is placed in JSON-RPC `auth` | [API tokens](https://www.zabbix.com/documentation/5.4/en/manual/api/reference/token) |

`problem.get` does not provide arbitrarily old resolved history. Use the helper's bounded history command, which calls `event.get` with `source: 0`, `object: 0`, `value: 1`, `time_from`, and `time_till` fixed as described above.

## Complete `host.create` params example

```json
{
  "host": "edge-1",
  "interfaces": [
    {"type": 1, "main": 1, "useip": 1, "ip": "192.0.2.10", "dns": "", "port": "10050"}
  ],
  "groups": [{"groupid": "2"}]
}
```

See the linked upstream pages for complete object schemas and field constraints.
