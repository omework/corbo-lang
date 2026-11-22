/* SPDX-License-Identifier: MIT OR Apache-2.0 */
/** Deterministic registration/notification witness shared by both runtimes. */
#define CHECK(x) do { if(!(x)) { fprintf(stderr,"channel check failed at %d\n",__LINE__);abort(); } } while(0)
int main(void) {
    reserve(1);
    uintptr_t c=channel_create(1,sizeof(uint64_t));
    uint64_t value=0,out=0,epoch=0;
    Task first={0},second={0};
    first.blocking=second.blocking=true;
    first.parked=second.parked=true;
    /* Empty check and registration use one epoch; sending publishes before wake. */
    CHECK(channel_receive(c,&out,&epoch,false)==1);
    CHECK(!channel_poll(&first,c,epoch,false));
    CHECK(!channel_poll(&second,c,epoch,false));
    CHECK(first.waiting&&second.waiting);
    value=41;CHECK(channel_send(c,&value,&epoch,false)==0&&value==0);
    CHECK(!first.waiting&&second.waiting);
    /* Dropping the selected wait frame forwards its notification. */
    channel_detach(&first);
    CHECK(!second.waiting);
    CHECK(channel_poll(&second,c,0,false));
    CHECK(!first.mutex_owner&&!second.mutex_owner);
    CHECK(channel_receive(c,&out,&epoch,false)==0&&out==41);
    /* A send between failed receive and registration cannot lose its wake. */
    CHECK(channel_receive(c,&out,&epoch,false)==1);
    uint64_t observed=epoch;
    value=42;CHECK(channel_send(c,&value,&epoch,false)==0);
    CHECK(channel_poll(&first,c,observed,false));
    /* Full senders are unlinked and woken together on close. */
    value=43;CHECK(channel_send(c,&value,&epoch,false)==1&&value==43);
    CHECK(!channel_poll(&first,c,epoch,true));
    CHECK(!channel_poll(&second,c,epoch,true));
    channel_close(c);channel_close(c);
    CHECK(!first.waiting&&!second.waiting);
    CHECK(channel_poll(&first,c,epoch,true));CHECK(channel_poll(&second,c,epoch,true));
    CHECK(channel_send(c,&value,&epoch,false)==2&&value==43);
    CHECK(channel_receive(c,&out,&epoch,false)==0&&out==42);
    CHECK(channel_receive(c,&out,&epoch,false)==2);
    channel_destroy(c);
    /* Removing an unnotified waiter leaves no pointer into reclaimed task state. */
    c=channel_create(1,sizeof(value));
    CHECK(channel_receive(c,&out,&epoch,false)==1);
    CHECK(!channel_poll(&first,c,epoch,false));channel_detach(&first);
    CHECK(!first.mutex_owner&&!first.channel_wait);
    channel_close(c);channel_destroy(c);
    region_release();release();
    return 0;
}
