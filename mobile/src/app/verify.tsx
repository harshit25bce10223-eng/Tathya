import {useCallback,useRef,useState} from 'react';
import {Text,View} from 'react-native';
import {CameraView,useCameraPermissions} from 'expo-camera';
import {useFocusEffect,useLocalSearchParams} from 'expo-router';
import {passportToken,request,usablePassport,type Passport} from '../lib/api';
import {Action,Input,Page,styles} from '../components/UI';
export default function Verify(){
 const params=useLocalSearchParams<{token?:string}>();
 const [input,setInput]=useState(params.token||''),[scan,setScan]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState(''),[result,setResult]=useState<Passport|null>(null),[permission,requestPermission]=useCameraPermissions(),[focused,setFocused]=useState(false),scanned=useRef(false);
 useFocusEffect(useCallback(()=>{setFocused(true);return()=>setFocused(false);},[]));
 const verify=async()=>{setBusy(true);setError('');setResult(null);try{setResult(await request<Passport>(`/verify/${passportToken(input)}`,{},false));}catch(e){setError(e instanceof Error?e.message:'Verification unavailable.');}finally{setBusy(false);}};
 return <Page><Text style={styles.title}>Verify the signed record.</Text><Input label="Passport token or verification link" value={input} onChangeText={v=>{setInput(v);setResult(null);}} autoCapitalize="none"/><Action title={busy?'Checking…':'Verify passport'} disabled={busy||!input.trim()} onPress={verify}/><Action title={scan?'Close scanner':'Scan QR code'} onPress={async()=>{if(scan){setScan(false);return;}if(permission?.granted||(await requestPermission()).granted){scanned.current=false;setScan(true);}else setError('Camera permission declined. Paste a token instead.');}}/>{scan&&focused&&permission?.granted&&<CameraView style={{height:300}} barcodeScannerSettings={{barcodeTypes:['qr']}} onBarcodeScanned={({data})=>{if(scanned.current)return;scanned.current=true;setInput(data);setResult(null);setScan(false);}}/>}{!!error&&<Text accessibilityRole="alert" style={styles.error}>{error}</Text>}{result&&<View style={styles.card}><Text style={styles.score}>{usablePassport(result)?`${result.trust_score}/100`:'Not currently assessed'}</Text><Text style={styles.text}>{result.requires_reassessment?'Sources or review changed. A fresh audit is required.':result.detail||'Read evidence and findings alongside this score.'}</Text><Text style={styles.text}>Signature: {result.signature_valid===true?'valid':'not verified'} · History: {result.chain?.ok?'valid':'not verified'}</Text><Text selectable style={styles.text}>{result.document_count} documents · {result.document_hash}</Text></View>}</Page>;
}
