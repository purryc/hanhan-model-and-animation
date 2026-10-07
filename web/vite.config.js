import {defineConfig} from 'vite';
import {writeFile} from 'node:fs/promises';

// Local development export only: fixed path, same-origin, bounded request size.
export default defineConfig({base:process.env.VITE_BASE_PATH||'/',plugins:[{
  name:'hanhan-local-video-export',
  configureServer(server){
    server.middlewares.use('/local-export/overview',async(req,res,next)=>{
      if(req.method!=='POST')return next();
      if(req.headers.origin!==`http://${req.headers.host}`){res.statusCode=403;return res.end();}
      const chunks=[];let size=0;
      try{
        for await(const chunk of req){size+=chunk.length;if(size>100*1024*1024){res.statusCode=413;return res.end();}chunks.push(chunk);}
        const v=new URL(req.url,'http://localhost').searchParams.get('version');
        const filename=v==='3'?'hanhan_mobile_v3_overview.webm':v==='4.7'?'hanhan_rodin_v4_7_overview.webm':v==='4.6'?'hanhan_rodin_v4_6_overview.webm':v==='4.5'?'hanhan_rodin_v4_5_overview.webm':v==='4.4'?'hanhan_rodin_v4_4_overview.webm':v==='4.3'?'hanhan_rodin_v4_3_overview.webm':v==='4.2'?'hanhan_rodin_v4_2_overview.webm':v==='4.1'?'hanhan_rodin_v4_1_overview.webm':'hanhan_rodin_v4_overview.webm';
        await writeFile(new URL('../output/'+filename,import.meta.url),Buffer.concat(chunks));
        res.statusCode=200;res.end('saved');
      }catch{res.statusCode=500;res.end('export failed');}
    });
  }
}]});
