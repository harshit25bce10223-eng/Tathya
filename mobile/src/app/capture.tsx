import {useCallback,useRef,useState} from 'react';
import {Image,Text} from 'react-native';
import {CameraView,useCameraPermissions} from 'expo-camera';
import {router,useFocusEffect} from 'expo-router';
import {Action,Page,styles} from '../components/UI';
import {uploadAssets} from '../lib/upload';
export default function Capture(){
 const camera=useRef<CameraView>(null),[focused,setFocused]=useState(false),[permission,requestPermission]=useCameraPermissions(),[photo,setPhoto]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState('');
 useFocusEffect(useCallback(()=>{setFocused(true);return()=>setFocused(false);},[]));
 const run=async(task:()=>Promise<void>)=>{setBusy(true);setError('');try{await task();}catch(e){setError(e instanceof Error?e.message:'Could not scan image.');}finally{setBusy(false);}};
 return <Page><Text style={styles.text}>Capture a readable document. OCR runs on your server. Add reference sources in the web workspace for verification.</Text>{!permission?.granted?<Action title="Allow camera" onPress={()=>run(async()=>{if(!(await requestPermission()).granted)setError('Camera permission declined. Choose a document on the home screen instead.');})}/>:photo?<Image source={{uri:photo}} accessibilityLabel="Captured document preview" style={{height:360,width:'100%',resizeMode:'contain'}}/>:focused&&<CameraView ref={camera} style={{height:360}}/>}{permission?.granted&&!photo&&<Action title="Capture document" disabled={busy} onPress={()=>run(async()=>{const image=await camera.current?.takePictureAsync({quality:0.8});if(image)setPhoto(image.uri);})}/ >}{!!photo&&<><Action title="Retake" disabled={busy} onPress={()=>setPhoto('')}/><Action title={busy?'Uploading…':'Upload this image'} disabled={busy} onPress={()=>run(async()=>{const a=await uploadAssets([{uri:photo,name:'scanned-document.jpg',mimeType:'image/jpeg'}]);router.replace(`/audit/${a.id}`);})}/></>}{!!error&&<Text accessibilityRole="alert" style={styles.error}>{error}</Text>}</Page>;
}
