import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';
let base = process.env.EXPO_PUBLIC_API_URL || '';
let bearer: string | null = null;
export function validateServer(input: string) {
 const u = new URL(input.trim());
 if (!['https:', 'http:'].includes(u.protocol) || u.username || u.password || u.search || u.hash || !['', '/'].includes(u.pathname)) throw new Error('Enter the server origin, for example https://tathya.example.com.');
 if (u.protocol !== 'https:' && !__DEV__) throw new Error('Use HTTPS for a release build.');
 return u.origin;
}
export function passportToken(input: string) {
 const text = input.trim(); if (/^[A-Za-z0-9_-]{8,128}$/.test(text)) return text;
 const u = new URL(text), match = u.pathname.match(/^\/(?:api\/v1\/)?verify\/([A-Za-z0-9_-]{8,128})\/?$/);
 if (u.origin !== base || !match || u.search || u.hash || u.username || u.password) throw new Error('Use a passport token or a verification link from your configured server.');
 return match[1];
}
export async function restore() {
 if (Platform.OS !== 'web') { base = (await SecureStore.getItemAsync('tathya.server')) || base; bearer = await SecureStore.getItemAsync('tathya.token'); }
 if (base) base = validateServer(base);
 return { base, signedIn: !!bearer };
}
export async function logout() { bearer = null; if (Platform.OS !== 'web') await SecureStore.deleteItemAsync('tathya.token'); }
export async function setServer(input: string) { const next = validateServer(input); if (next !== base) await logout(); base = next; if (Platform.OS !== 'web') await SecureStore.setItemAsync('tathya.server', base); }
export async function request<T>(path: string, init: RequestInit = {}, authenticated = true): Promise<T> {
 if (!base) throw new Error('Set your server first.'); if (authenticated && !bearer) throw new Error('Sign in to open your audits.');
 base = validateServer(base);
 const c = new AbortController(), timer = setTimeout(() => c.abort(), 120000);
 try {
  const headers = new Headers(init.headers); if (authenticated && bearer) headers.set('Authorization', `Bearer ${bearer}`);
  const r = await fetch(`${base}/api/v1${path}`, { ...init, headers, signal: c.signal }), data = await r.json();
  if (r.status === 401 && authenticated) await logout();
  if (!r.ok) throw new Error(typeof data.detail === 'string' ? data.detail : `The service returned ${r.status}.`);
  return data as T;
 } catch (e) { if (c.signal.aborted) throw new Error('Request timed out. Check the audit before retrying an upload.'); throw e; } finally { clearTimeout(timer); }
}
export async function login(email: string, password: string) {
 const r = await request<{access_token:string}>('/login/access-token', { method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded'}, body:new URLSearchParams({username:email.trim(),password}).toString() }, false);
 if (!r.access_token) throw new Error('The server did not return a valid session.');
 if (Platform.OS !== 'web') await SecureStore.setItemAsync('tathya.token',r.access_token); bearer = r.access_token;
}
export type Summary = {audit:{id:string;title:string;status:string;error_message?:string};verify_token:string|null};
export type Finding = {id:string;type:string;severity:string;status:string;explanation:string;evidence?:{quote:string}[]};
export type Passport = {found:boolean;trust_score:number;score_status:string;requires_reassessment:boolean;signature_valid:boolean|null;chain:{ok:boolean}|null;document_count:number;document_hash:string;detail?:string};
export function usablePassport(p:Passport) { return p.found === true && p.signature_valid === true && p.chain?.ok === true && p.requires_reassessment === false && ['assessed','partial_verification'].includes(p.score_status) && Number.isFinite(p.trust_score) && p.trust_score >= 0 && p.trust_score <= 100; }
