import { describe, it, expect } from 'vitest';
import yaml from 'js-yaml';
import { createApp } from '../src/app/createApp.jsx';
import { MemoryKVAdapter } from '../src/adapters/kv/memoryKv.js';

const node = 'vless://00000000-0000-4000-8000-000000000001@example.com:443?encryption=none#compatibility';
const query = new URLSearchParams({ config: node, selectedRules: 'balanced' }).toString();

describe('personal gateway compatibility', () => {
    it('keeps the Clash structure consumed by the personal gateway', async () => {
        const app = createApp({ kv: new MemoryKVAdapter(), config: {}, logger: console });
        const response = await app.request('https://sub.397256.xyz/clash?' + query);
        expect(response.status).toBe(200);
        const config = yaml.load(await response.text());
        expect(config.proxies.some(p => p.type === 'vless' && p.server === 'example.com')).toBe(true);
        expect(Array.isArray(config['proxy-groups'])).toBe(true);
        expect(Array.isArray(config.rules)).toBe(true);
        expect(Object.keys(config['rule-providers']).length).toBeGreaterThan(0);
        for (const p of Object.values(config['rule-providers'])) {
            expect(p.type).toBe('http');
            expect(p.url).toMatch(/^https:\/\//);
        }
    });

    it('resolves an existing short-link value without rewriting it', async () => {
        const kv = new MemoryKVAdapter();
        await kv.put('existing-link', '?' + query);
        const app = createApp({ kv, config: {}, logger: console });
        const response = await app.request('https://sub.397256.xyz/c/existing-link');
        expect(response.status).toBe(302);
        expect(response.headers.get('location')).toBe('https://sub.397256.xyz/clash?' + query);
        expect(await kv.get('existing-link')).toBe('?' + query);
    });
});
