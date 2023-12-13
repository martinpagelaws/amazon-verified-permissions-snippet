forbid (
	principal,
	action in [
		SimplePosts::Action::"CreatePost"
	],
	resource
)
when {
	principal has custom &&
	principal.custom has appRole &&
	principal.custom.appRole == "admin"
};

