import {Stack} from 'expo-router';
import {StatusBar} from 'expo-status-bar';
export default function Layout(){return <><StatusBar style="dark"/><Stack screenOptions={{headerStyle:{backgroundColor:'#f8f7f3'},headerTintColor:'#214c3b'}}><Stack.Screen name="index" options={{title:'Tathya Scan'}}/><Stack.Screen name="verify" options={{title:'Verify passport'}}/><Stack.Screen name="capture" options={{title:'Scan document'}}/><Stack.Screen name="audit/[id]" options={{title:'Audit result'}}/></Stack></>;}
