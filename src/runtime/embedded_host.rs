//! Rust-owned host facade for a persistent, explicitly polled local actor runtime.
//!
//! Native actor behaviors are function pointers today, not captured closures.
//! No C actor ABI or automatic background scheduler is implied.

#[cfg(test)]
mod tests {
    use super::*;
    use crate::runtime::Actor;

    fn add_to_counter(actor: &mut Actor, args: &[Value]) {
        let increment = args.first().and_then(Value::as_int).unwrap_or(0);
        let current = actor
            .get_state_field("count")
            .and_then(|value| value.as_int())
            .unwrap_or(0);
        actor.set_state_field("count", Value::int(current + increment));
    }

    #[test]
    fn embedded_host_keeps_state_across_poll_calls_and_shuts_down() {
        let mut host = EmbeddedActorHost::new(2);
        let actor = host.spawn(vec![("count".to_string(), 0)]).unwrap();
        host.register_behavior(actor, "add", add_to_counter).unwrap();
        host.send_int(actor, "add", &[2]).unwrap();
        host.send_int(actor, "add", &[3]).unwrap();

        assert_eq!(host.poll(1).unwrap(), 1);
        assert_eq!(host.get_int_field(actor, "count"), Ok(Some(2)));
        assert_eq!(host.poll(1).unwrap(), 1);
        assert_eq!(host.get_int_field(actor, "count"), Ok(Some(5)));
        assert_eq!(host.poll(1).unwrap(), 0);

        host.shutdown();
        host.shutdown();
        assert_eq!(host.poll(1), Err(HostError::Stopped));
        assert_eq!(host.send_int(actor, "add", &[1]), Err(HostError::Stopped));
    }

    #[test]
    fn embedded_host_fails_closed_on_quota_or_unknown_actor_and_behavior() {
        let mut host = EmbeddedActorHost::new(1);
        let actor = host.spawn(vec![]).unwrap();
        assert_eq!(host.spawn(vec![]), Err(HostError::ActorLimitReached));
        assert_eq!(host.send_int(actor, "missing", &[]), Err(HostError::UnknownBehavior));
        assert_eq!(host.send_int(u64::MAX, "missing", &[]), Err(HostError::UnknownActor));
        assert_eq!(
            host.register_behavior(u64::MAX, "add", add_to_counter),
            Err(HostError::UnknownActor)
        );
    }

    #[test]
    fn embedded_host_rejects_integer_truncation_before_state_or_message_mutation() {
        let mut host = EmbeddedActorHost::new(2);
        assert_eq!(
            host.spawn(vec![("count".to_string(), i64::MAX)]),
            Err(HostError::IntegerOutOfRange)
        );
        let actor = host.spawn(vec![("count".to_string(), 7)]).unwrap();
        host.register_behavior(actor, "add", add_to_counter).unwrap();
        assert_eq!(
            host.send_int(actor, "add", &[i64::MAX]),
            Err(HostError::IntegerOutOfRange)
        );
        assert_eq!(host.poll(5).unwrap(), 0);
        assert_eq!(host.get_int_field(actor, "count"), Ok(Some(7)));
    }
}
