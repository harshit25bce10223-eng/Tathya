import {Platform} from 'react-native';
import type {DocumentPickerAsset} from 'expo-document-picker';
import {request} from './api';
export async function uploadAssets(assets:Pick<DocumentPickerAsset,'uri'|'name'|'mimeType'|'size'|'file'>[]){
 if(!assets.length||assets.length>20||assets.some(a=>a.size!==undefined&&(!a.size||a.size>50*1024*1024))||assets.reduce((n,a)=>n+(a.size||0),0)>100*1024*1024)throw new Error('Choose up to 20 non-empty files, at most 50 MB each and 100 MB total.');
 const form=new FormData();form.append('title',assets[0].name);
 for(const a of assets){if(Platform.OS==='web'){let file:Blob|undefined=a.file;if(!file&&a.uri.startsWith('data:image/'))file=await(await fetch(a.uri)).blob();if(!file||!file.size||file.size>50*1024*1024)throw new Error('Choose a non-empty file up to 50 MB again.');form.append('files',file,a.name);}else form.append('files',{uri:a.uri,name:a.name,type:a.mimeType||'application/octet-stream'} as unknown as Blob);}
 return request<{id:string}>('/audits',{method:'POST',body:form});
}
