/* SPDX-License-Identifier: MIT OR Apache-2.0 */
#include <assert.h>
int main(void){
 corbo_runtime_init(65536,0,65536);
#ifdef _WIN32
 assert(region_default_capacity()==4115);fake_available=0;assert(region_default_capacity()==0);
#else
 size_t capacity=region_default_capacity();assert(capacity>0&&capacity<=PTRDIFF_MAX);
#endif
 corbo_runtime_shutdown();puts("default capacity parity passed");
}
