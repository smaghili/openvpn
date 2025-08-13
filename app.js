import * as THREE from 'https://unpkg.com/three@0.157.0/build/three.module.js';
import {OrbitControls} from 'https://unpkg.com/three@0.157.0/examples/jsm/controls/OrbitControls.js';

const navButtons=document.querySelectorAll('.nav-btn');
const panels=document.querySelectorAll('.panel');
navButtons.forEach(btn=>btn.addEventListener('click',()=>{
 navButtons.forEach(b=>b.classList.remove('active'));
 btn.classList.add('active');
 panels.forEach(p=>p.classList.remove('active'));
 document.getElementById(btn.dataset.panel).classList.add('active');
}));

const container=document.getElementById('three-container');
const scene=new THREE.Scene();
const camera=new THREE.PerspectiveCamera(60,container.clientWidth/container.clientHeight,0.1,1000);
camera.position.set(0,5,10);
const renderer=new THREE.WebGLRenderer({antialias:true,alpha:true});
renderer.setSize(container.clientWidth,container.clientHeight);
renderer.setPixelRatio(window.devicePixelRatio);
container.appendChild(renderer.domElement);
const controls=new OrbitControls(camera,renderer.domElement);
controls.enableDamping=true;
const light=new THREE.DirectionalLight(0xffffff,1);
light.position.set(5,10,7);
scene.add(light);
scene.add(new THREE.AmbientLight(0xffffff,0.3));
const nodes=[];
const nodeGeo=new THREE.SphereGeometry(0.3,16,16);
for(let i=0;i<5;i++){
 const mat=new THREE.MeshStandardMaterial({color:0x007aff});
 const mesh=new THREE.Mesh(nodeGeo,mat);
 mesh.position.set(Math.random()*4-2,Math.random()*2-1,Math.random()*4-2);
 mesh.userData={id:i,name:`Server-${i+1}`};
 scene.add(mesh);
 nodes.push(mesh);
}
const raycaster=new THREE.Raycaster();
const pointer=new THREE.Vector2();
function onPointerMove(e){
 const r=renderer.domElement.getBoundingClientRect();
 pointer.x=(e.clientX-r.left)/r.width*2-1;
 pointer.y=-(e.clientY-r.top)/r.height*2+1;
}
function onClick(){
 raycaster.setFromCamera(pointer,camera);
 const inter=raycaster.intersectObjects(nodes);
 if(inter.length)selectServer(inter[0].object.userData.id);
}
renderer.domElement.addEventListener('pointermove',onPointerMove);
renderer.domElement.addEventListener('click',onClick);
let paused=false;
function render(){
 controls.update();
 renderer.render(scene,camera);
 if(!paused)requestAnimationFrame(render);
}
render();
window.addEventListener('resize',()=>{
 const w=container.clientWidth;
 const h=container.clientHeight;
 camera.aspect=w/h;
 camera.updateProjectionMatrix();
 renderer.setSize(w,h);
});
document.addEventListener('visibilitychange',()=>{
 paused=document.hidden;
 if(!paused)requestAnimationFrame(render);
});

const servers=[{name:'Server-1',status:'online',cpu:25,ram:40},{name:'Server-2',status:'online',cpu:35,ram:50},{name:'Server-3',status:'offline',cpu:0,ram:0},{name:'Server-4',status:'online',cpu:15,ram:30},{name:'Server-5',status:'online',cpu:45,ram:70}];
const users=[{name:'Alice',sessions:1,device:'macOS'},{name:'Bob',sessions:2,device:'Windows'},{name:'Carol',sessions:0,device:'Linux'}];

function populateServers(){
 const tbody=document.querySelector('#server-table tbody');
 tbody.innerHTML='';
 servers.forEach((s,i)=>{
  const tr=document.createElement('tr');
  tr.dataset.id=i;
  tr.innerHTML=`<td>${s.name}</td><td>${s.status}</td><td>${s.cpu}%</td><td>${s.ram}%</td><td><button data-a='start'>Start</button> <button data-a='stop'>Stop</button></td>`;
  tbody.appendChild(tr);
 });
 document.getElementById('online-count').textContent=servers.filter(s=>s.status==='online').length;
}
function populateUsers(){
 const tbody=document.querySelector('#user-table tbody');
 tbody.innerHTML='';
 users.forEach(u=>{
  const tr=document.createElement('tr');
  tr.innerHTML=`<td>${u.name}</td><td>${u.sessions}</td><td>${u.device}</td><td><button data-a='disable'>Disable</button></td>`;
  tbody.appendChild(tr);
 });
 document.getElementById('session-count').textContent=users.reduce((a,b)=>a+b.sessions,0);
}
populateServers();
populateUsers();

function selectServer(id){
 nodes.forEach(n=>n.material.emissive.setHex(0x000000));
 const target=nodes.find(n=>n.userData.id===id);
 if(target)target.material.emissive.setHex(0x005bb5);
 const rows=document.querySelectorAll('#server-table tbody tr');
 rows.forEach(r=>r.classList.toggle('active',Number(r.dataset.id)===id));
}

function toggleTheme(){
 const root=document.documentElement;
 const theme=root.getAttribute('data-theme')==='dark'?'light':'dark';
 root.setAttribute('data-theme',theme);
}

document.getElementById('theme-toggle').addEventListener('click',toggleTheme);
document.getElementById('settings-theme-toggle').addEventListener('click',toggleTheme);

const palette=document.getElementById('command-palette');
document.addEventListener('keydown',e=>{
 if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='k'){
  e.preventDefault();
  palette.hidden=false;
  document.getElementById('command-input').focus();
 }
 if(e.key==='Escape'&&!palette.hidden)palette.hidden=true;
});

function toast(msg){
 const div=document.createElement('div');
 div.className='toast';
 div.textContent=msg;
 document.getElementById('toast-container').appendChild(div);
 setTimeout(()=>div.remove(),4000);
}
toast('Welcome');

const chart=document.getElementById('tunnel-chart');
const ctx=chart.getContext('2d');
chart.width=200;chart.height=60;
const points=[];
function draw(){
 ctx.clearRect(0,0,chart.width,chart.height);
 ctx.strokeStyle=getComputedStyle(document.documentElement).getPropertyValue('--color-primary');
 ctx.beginPath();
 points.forEach((v,i)=>{
  const x=i/(points.length-1)*chart.width;
  const y=chart.height-v;
  if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y);
 });
 ctx.stroke();
}
setInterval(()=>{
 if(points.length>30)points.shift();
 points.push(Math.random()*chart.height);
 draw();
},1000);
