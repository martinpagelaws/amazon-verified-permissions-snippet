permit (
	principal,
	action in [
		SimplePosts::Action::"DeletePost"
	],
	resource
)
when {
	resource has owner &&
	principal == resource.owner
};
