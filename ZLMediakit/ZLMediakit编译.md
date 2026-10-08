
## 1、获取代码

**请不要使用github 下载zip包的方式下载源码**，务必使用git克隆ZLMediaKit的代码，因为ZLMediaKit依赖于第三方代码，zip包不会下载第三方依赖源码，你可以这样操作：

```shell
#国内用户推荐从同步镜像网站gitee下载 
git clone --depth 1 https://gitee.com/xia-chu/ZLMediaKit
cd ZLMediaKit
#千万不要忘记执行这句命令
git submodule update --init
```

## 2、构建和编译项目


由于开启webrtc相关功能比较复杂，默认是不开启编译的，如果你对zlmediakit的webrtc功能比较感兴趣，可以参考[这里](https://github.com/ZLMediaKit/ZLMediaKit/wiki/zlm%E5%90%AF%E7%94%A8webrtc%E7%BC%96%E8%AF%91%E6%8C%87%E5%8D%97)

- 在linux或macOS系统下,你应该这样操作：

 ```shell
    cd ZLMediaKit
    mkdir build
    #macOS下可能需要这样指定openss路径：cmake .. -DOPENSSL_ROOT_DIR=/usr/local/Cellar/openssl/1.0.2j/
    cmake -S . -B build
    make -j4
    ```
        
 如果你要编译ios版本，可以生成xcode工程然后编译c api的静态库
 ```shell
    cd ZLMediaKit
    mkdir -p build
    cd build
    # 生成Xcode工程，工程文件在build目录下
    cmake .. -G Xcode -DCMAKE_TOOLCHAIN_FILE=../cmake/ios.toolchain.cmake  -DPLATFORM=OS64COMBINED
    ```

## 3、运行
    - 在macos下启动：
        
        ```shell
        cd ZLMediaKit/release/darwin/Debug
        #通过-h可以了解启动参数
        ./MediaServer -h
        #以守护进程模式启动
        ./MediaServer -d &

