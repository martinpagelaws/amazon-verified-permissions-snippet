permit (
	principal,
	action in [
		SimplePosts::Action::"DeletePost"
	],
	resource
)
when {
	principal has custom &&
	principal.custom has appRole &&
	principal.custom.appRole == "admin"
};
