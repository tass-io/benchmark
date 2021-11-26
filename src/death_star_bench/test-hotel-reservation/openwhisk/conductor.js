function main(params) {
    let depth = params.depth
    let path = params.path
    let here = path[depth]
    switch (here) {
        case "nginx": return { action: 'bench-05-hotel-nginx', params }
        case "check-reservation": return { action: 'bench-05-hotel-check-reservation', params }
        case "make-reservation": return { action: 'bench-05-hotel-make-reservation', params }
        case "get-profiles": return { action: 'bench-05-hotel-get-profiles', params }
        case "search": return { action: 'bench-05-hotel-search', params }
        default: return { params }
    }
}